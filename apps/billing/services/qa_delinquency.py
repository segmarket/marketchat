"""
Simulação do ciclo de inadimplência para QA (staging + Asaas sandbox).

Recusa produção: a URL e a chave Asaas precisam ser de sandbox e nenhum host configurado
pode ser de produção. Atua sobre um único tenant; o que muda estado local guarda os
valores anteriores em QaBillingSnapshot para restaurar o cenário.
"""

from __future__ import annotations

import contextlib
import time
import uuid
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Any, Callable, Iterator
from unittest import mock
from urllib.parse import urlparse

import requests
from django.conf import settings
from django.core.management import call_command
from django.db import transaction
from django.test import Client
from django.utils import timezone

from apps.accounts.models import User
from apps.billing.models import (
    AsaasWebhookEvent,
    QaBillingSnapshot,
    Subscription,
    SubscriptionCharge,
)
from apps.billing.services.asaas_client import AsaasAPIError, AsaasClient
from apps.billing.services.subscription_charges import (
    PAID_STATUSES,
    outstanding_charges,
    payment_status_of,
    payment_subscription_id_of,
)
from apps.tenants.billing_rules import billing_grace_period, grace_deadline
from apps.tenants.models import Tenant

SANDBOX_HOST = "api-sandbox.asaas.com"
SANDBOX_KEY_PREFIX = "$aact_hmlg_"
PRODUCTION_KEY_PREFIX = "$aact_prod_"
PRODUCTION_HOSTS = frozenset(
    {
        "marketchat.com.br",
        "www.marketchat.com.br",
        "app.marketchat.com.br",
        "api.marketchat.com.br",
    },
)

OVERDUE_EVENTS = ("PAYMENT_OVERDUE",)
PAID_EVENTS = ("PAYMENT_CONFIRMED", "PAYMENT_RECEIVED")
MAX_GENERATE_MONTHS_AHEAD = 6
PROBE_JID = "5500000000000@s.whatsapp.net"

PROTECTED_PATH = "/api/markets/"
ME_PATH = "/api/auth/me/"
LOGIN_PATH = "/api/auth/token/"
PAYMENT_SUMMARY_PATH = "/api/settings/billing/payment-method/"
REGULARIZE_PATH = "/api/settings/billing/regularize/"

TENANT_SNAPSHOT_FIELDS = (
    "subscription_status",
    "overdue_since",
    "billing_blocked_at",
    "whatsapp_logout_pending_since",
    "whatsapp_logout_attempts",
    "whatsapp_logout_last_attempt_at",
    "whatsapp_logout_last_error",
)
_DATETIME_FIELDS = frozenset(
    {
        "overdue_since",
        "billing_blocked_at",
        "whatsapp_logout_pending_since",
        "whatsapp_logout_last_attempt_at",
    },
)

PREPARE_CHARGE_HELP = (
    "Nenhuma cobrança PENDING da assinatura está elegível para forçar o vencimento.\n"
    "Como preparar (sempre cobranças da própria assinatura, nunca avulsas):\n"
    "  1. Se o tenant ainda está no trial com a 1ª cobrança PENDING, ela já é elegível.\n"
    "  2. Gere as cobranças futuras da assinatura no sandbox:\n"
    "       qa_billing_delinquency generate-charges --tenant-id <id> --confirm-slug <slug> --until AAAA-MM\n"
    "     (GET /v3/subscriptions/{id}/paymentBook; no sandbox antecipa as cobranças até o mês informado).\n"
    "  3. Rode diagnose de novo e use a cobrança PENDING listada em --payment-id.\n"
    "Cobranças CONFIRMED/RECEIVED não podem voltar a vencer; cobranças já OVERDUE só precisam\n"
    "do webhook processado (confira a lista 'Divergências' do diagnose)."
)


class QaEnvironmentError(Exception):
    """Ambiente não é QA/sandbox."""


class QaActionError(Exception):
    """Ação recusada ou pré-condição ausente."""


@dataclass
class Check:
    name: str
    ok: bool
    detail: str
    source: str


@dataclass
class Report:
    """Saída do comando: linhas livres e verificações com a origem da evidência."""

    write: Callable[[str], None]
    checks: list[Check] = field(default_factory=list)

    def line(self, text: str = "") -> None:
        self.write(text)

    def check(self, name: str, ok: bool, detail: str = "", *, source: str = "LOCAL") -> bool:
        self.checks.append(Check(name=name, ok=ok, detail=detail, source=source))
        mark = "OK   " if ok else "FALHA"
        self.write(f"  [{mark}] [{source}] {name}" + (f": {detail}" if detail else ""))
        return ok

    @property
    def failed(self) -> list[Check]:
        return [c for c in self.checks if not c.ok]


# --------------------------------------------------------------------------- guardas


def _configured_hosts() -> set[str]:
    hosts: set[str] = set()
    for host in getattr(settings, "ALLOWED_HOSTS", None) or []:
        hosts.add(str(host).strip().lstrip(".").lower())
    for name in ("CSRF_TRUSTED_ORIGINS", "CORS_ALLOWED_ORIGINS"):
        for origin in getattr(settings, name, None) or []:
            hosts.add((urlparse(str(origin)).hostname or "").lower())
    for name in ("FRONTEND_APP_ORIGIN", "PUBLIC_WEBHOOK_BASE_URL", "MARKETING_PUBLIC_ORIGIN"):
        hosts.add((urlparse(str(getattr(settings, name, "") or "")).hostname or "").lower())
    hosts.discard("")
    return hosts


def _is_sandbox_url(url: str) -> bool:
    parsed = urlparse(url or "")
    return parsed.scheme == "https" and (parsed.hostname or "").lower() == SANDBOX_HOST


def environment_problems() -> list[str]:
    problems: list[str] = []
    url = str(getattr(settings, "ASAAS_API_URL", "") or "")
    if not _is_sandbox_url(url):
        problems.append(f"ASAAS_API_URL fora do sandbox (host={urlparse(url).hostname or '-'}).")
    key = str(getattr(settings, "ASAAS_API_KEY", "") or "").strip()
    if key.startswith(PRODUCTION_KEY_PREFIX):
        problems.append("ASAAS_API_KEY é uma chave de produção.")
    elif not key.startswith(SANDBOX_KEY_PREFIX):
        problems.append("ASAAS_API_KEY ausente ou sem o prefixo de sandbox.")
    production = sorted(_configured_hosts() & PRODUCTION_HOSTS)
    if production:
        problems.append(f"Configuração com host de produção: {', '.join(production)}.")
    return problems


def assert_qa_environment() -> None:
    problems = environment_problems()
    if problems:
        raise QaEnvironmentError("Recusado: ambiente não é QA/sandbox. " + " ".join(problems))


class SandboxAsaasClient(AsaasClient):
    """AsaasClient restrito ao sandbox, com as ações exclusivas de sandbox."""

    def __init__(self) -> None:
        super().__init__()
        if not _is_sandbox_url(self.base_url):
            raise QaEnvironmentError("Recusado: cliente Asaas fora do sandbox.")

    def list_subscription_payments(self, subscription_id: str, **params: Any) -> list[dict[str, Any]]:
        data = self._request("GET", f"/subscriptions/{subscription_id}/payments", params=params)
        body = self._require_dict_response(data, context="list_subscription_payments")
        return [p for p in body.get("data") or [] if isinstance(p, dict)]

    def list_webhooks(self) -> list[dict[str, Any]]:
        data = self._request("GET", "/webhooks")
        body = self._require_dict_response(data, context="list_webhooks")
        return [w for w in body.get("data") or [] if isinstance(w, dict)]

    def force_overdue(self, payment_id: str) -> dict[str, Any]:
        data = self._request("POST", f"/sandbox/payment/{payment_id}/overdue", {})
        return data if isinstance(data, dict) else {}

    def confirm_payment(self, payment_id: str) -> dict[str, Any]:
        data = self._request("POST", f"/sandbox/payment/{payment_id}/confirm", {})
        return data if isinstance(data, dict) else {}

    def generate_payment_book(self, subscription_id: str, *, month: int, year: int) -> int:
        """O carnê vem em PDF (descartado); no sandbox a chamada antecipa as cobranças futuras."""
        url = f"{self.base_url}/subscriptions/{subscription_id}/paymentBook"
        try:
            response = requests.get(
                url,
                params={"month": month, "year": year},
                headers=self._headers(),
                timeout=90,
            )
        except requests.RequestException as exc:
            raise AsaasAPIError(f"Falha de rede Asaas: {exc}") from exc
        if response.status_code >= 400:
            try:
                payload: Any = response.json()
            except ValueError:
                payload = response.text[:500]
            raise AsaasAPIError("Erro na API Asaas", status_code=response.status_code, payload=payload)
        return len(response.content or b"")


# --------------------------------------------------------------------------- utilitários


@contextlib.contextmanager
def rolled_back() -> Iterator[None]:
    """Executa o código real e descarta qualquer escrita no banco."""
    with transaction.atomic():
        yield
        transaction.set_rollback(True)


def load_tenant(tenant_id: int) -> Tenant:
    tenant = Tenant.objects.filter(pk=tenant_id).first()
    if tenant is None:
        raise QaActionError(f"Tenant {tenant_id} não encontrado.")
    return tenant


def subscription_of(tenant: Tenant) -> Subscription | None:
    return Subscription.objects.filter(tenant=tenant).first()


def require_subscription(tenant: Tenant) -> Subscription:
    sub = subscription_of(tenant)
    if sub is None or not sub.asaas_subscription_id or not sub.asaas_customer_id:
        raise QaActionError(
            f"Tenant {tenant.pk} sem assinatura Asaas local (asaas_subscription_id/customer_id).",
        )
    return sub


def _fmt_dt(value: datetime | None) -> str:
    return timezone.localtime(value).strftime("%d/%m/%Y %H:%M:%S %Z") if value else "-"


def _asaas_datetime(value: datetime) -> str:
    return timezone.localtime(value).strftime("%Y-%m-%d %H:%M:%S")


def asaas_error_text(exc: AsaasAPIError) -> str:
    payload = exc.payload
    if isinstance(payload, dict):
        errors = payload.get("errors")
        if isinstance(errors, list) and errors and isinstance(errors[0], dict):
            return f"HTTP {exc.status_code}: {errors[0].get('description') or errors[0].get('code')}"
    return f"HTTP {exc.status_code or '-'}: {exc}"


def _serialize(value: Any) -> Any:
    return value.isoformat() if isinstance(value, datetime) else value


def _deserialize(name: str, value: Any) -> Any:
    if name in _DATETIME_FIELDS or name.endswith("_at"):
        return datetime.fromisoformat(value) if value else None
    return value


def capture_state(tenant: Tenant, sub: Subscription | None) -> dict[str, Any]:
    fresh = Tenant.objects.get(pk=tenant.pk)
    state: dict[str, Any] = {
        "tenant": {name: _serialize(getattr(fresh, name)) for name in TENANT_SNAPSHOT_FIELDS},
        "subscription": None,
        "charges": [],
    }
    if sub is not None:
        fresh_sub = Subscription.objects.get(pk=sub.pk)
        state["subscription"] = {"id": fresh_sub.pk, "status": fresh_sub.status}
        state["charges"] = [
            {
                "id": c.pk,
                "asaas_payment_id": c.asaas_payment_id,
                "overdue_at": _serialize(c.overdue_at),
                "paid_at": _serialize(c.paid_at),
                "removed_at": _serialize(c.removed_at),
            }
            for c in SubscriptionCharge.objects.filter(subscription=fresh_sub).order_by("pk")
        ]
    return state


def _state_diff(before: dict[str, Any], after: dict[str, Any]) -> list[str]:
    """Diferenças before → after; cobranças que só existem em before não entram."""
    diffs: list[str] = []
    for name in TENANT_SNAPSHOT_FIELDS:
        if before["tenant"].get(name) != after["tenant"].get(name):
            diffs.append(f"tenant.{name}: {before['tenant'].get(name)} → {after['tenant'].get(name)}")
    if before["subscription"] != after["subscription"]:
        diffs.append(f"subscription: {before['subscription']} → {after['subscription']}")
    old = {c["asaas_payment_id"]: c for c in before["charges"]}
    for charge in after["charges"]:
        previous = old.get(charge["asaas_payment_id"])
        if previous != charge:
            diffs.append(f"cobrança {charge['asaas_payment_id']}: {previous} → {charge}")
    return diffs


def panel_access_preview(tenant: Tenant) -> bool:
    """has_panel_access() real (pode suspender na request), com as escritas descartadas."""
    with rolled_back():
        return Tenant.objects.get(pk=tenant.pk).has_panel_access()


def _subscription_payments(client: SandboxAsaasClient, sub: Subscription) -> list[dict[str, Any]]:
    payments = client.list_subscription_payments(sub.asaas_subscription_id, limit=100)
    return sorted(payments, key=lambda p: (str(p.get("dueDate") or ""), str(p.get("id") or "")))


def _require_payment_of_subscription(
    client: SandboxAsaasClient,
    sub: Subscription,
    payment_id: str,
) -> dict[str, Any]:
    try:
        payment = client.get_payment(payment_id)
    except AsaasAPIError as exc:
        raise QaActionError(f"Cobrança {payment_id} não encontrada no sandbox ({asaas_error_text(exc)}).") from exc
    if payment_subscription_id_of(payment) != sub.asaas_subscription_id:
        raise QaActionError(
            f"Cobrança {payment_id} não pertence à assinatura {sub.asaas_subscription_id} do tenant.",
        )
    if payment.get("deleted"):
        raise QaActionError(f"Cobrança {payment_id} está removida no Asaas.")
    return payment


def wait_for_webhook(
    report: Report,
    *,
    payment_id: str,
    events: tuple[str, ...],
    since: datetime,
    timeout: int,
    poll_seconds: float = 3.0,
) -> AsaasWebhookEvent | None:
    """Aguarda o webhook real do Asaas ser processado pelo staging (sem simular nada)."""
    deadline = time.monotonic() + max(0, timeout)
    while True:
        record = (
            AsaasWebhookEvent.objects.filter(
                asaas_payment_id=payment_id,
                event__in=events,
                received_at__gte=since,
                processed_at__isnull=False,
            )
            .order_by("-received_at")
            .first()
        )
        if record is not None:
            report.check(
                "Webhook real recebido e processado",
                True,
                f"{record.event} outcome={record.outcome} evento={record.event_key}",
                source="SANDBOX",
            )
            return record
        if time.monotonic() >= deadline:
            report.check(
                "Webhook real recebido e processado",
                False,
                f"nenhum {'/'.join(events)} para {payment_id} em {timeout}s. Rode diagnose: "
                "fila do webhook interrompida, URL errada ou token divergente.",
                source="SANDBOX",
            )
            return None
        time.sleep(poll_seconds)


# --------------------------------------------------------------------------- diagnose


def _count(model_path: str, tenant: Tenant) -> int:
    from django.apps import apps

    model = apps.get_model(model_path)
    manager = getattr(model, "all_objects", model.objects)
    return manager.filter(tenant_id=tenant.pk).count()


def report_tenant_state(report: Report, tenant: Tenant) -> None:
    from apps.billing.services.subscription_enforcement import suspension_reason_for_tenant

    tenant.refresh_from_db()
    now = timezone.now()
    grace_end = tenant.grace_ends_at()
    report.line(f"Tenant {tenant.pk} slug={tenant.slug} nome={tenant.name!r}")
    report.line(f"  status={tenant.subscription_status} trial_ends_at={_fmt_dt(tenant.trial_ends_at)}")
    report.line(
        f"  overdue_since={_fmt_dt(tenant.overdue_since)} "
        f"BILLING_GRACE_DAYS={billing_grace_period().days}",
    )
    if grace_end is not None:
        situation = "em carência" if now < grace_end else "carência encerrada"
        report.line(f"  fim da carência={_fmt_dt(grace_end)} ({situation})")
    else:
        report.line("  fim da carência=- (tenant não está OVERDUE)")
    report.line(f"  billing_blocked_at={_fmt_dt(tenant.billing_blocked_at)}")
    notified = tenant.billing_suspension_notified_at
    if tenant.billing_blocked_at is None:
        email_state = "-"
    elif notified is not None and notified >= tenant.billing_blocked_at:
        email_state = f"enviado em {_fmt_dt(notified)}"
    else:
        email_state = "pendente (check_subscriptions envia)"
    report.line(f"  e-mail de suspensão: {email_state}")
    report.line(
        f"  logout Evolution: pendente_desde={_fmt_dt(tenant.whatsapp_logout_pending_since)} "
        f"tentativas={tenant.whatsapp_logout_attempts} "
        f"ultima={_fmt_dt(tenant.whatsapp_logout_last_attempt_at)} "
        f"ultimo_erro={tenant.whatsapp_logout_last_error or '-'}",
    )
    report.line(
        f"  acesso: painel={'sim' if panel_access_preview(tenant) else 'não'} "
        f"bot={'sim' if tenant.has_messaging_access() else 'não'}",
    )
    reason = suspension_reason_for_tenant(tenant, now=now)
    report.line(f"  check_subscriptions agora: {('suspenderia (' + reason + ')') if reason else 'nada a fazer'}")


def report_ledger(report: Report, sub: Subscription) -> None:
    charges = list(SubscriptionCharge.objects.filter(subscription=sub).order_by("original_due_date", "due_date", "pk"))
    report.line(f"Cobranças no ledger local ({len(charges)}):")
    for c in charges:
        flag = "EXIGIDA" if c.is_outstanding else ("paga" if c.paid_at else ("removida" if c.removed_at else "-"))
        report.line(
            f"  {c.asaas_payment_id} competência={c.competence or '-'} venc={c.due_date or '-'} "
            f"valor={c.value if c.value is not None else '-'} asaas={c.asaas_status or '-'} [{flag}] "
            f"exigida_em={_fmt_dt(c.overdue_at)} paga_em={_fmt_dt(c.paid_at)} ultimo_evento={c.last_event or '-'}",
        )
    required = list(outstanding_charges(sub))
    report.line(f"Cobranças exigidas: {', '.join(c.asaas_payment_id for c in required) or 'nenhuma'}")
    events = list(
        AsaasWebhookEvent.objects.filter(asaas_subscription_id=sub.asaas_subscription_id).order_by("-received_at")[:10],
    )
    report.line(f"Últimos webhooks da assinatura ({len(events)}):")
    for e in events:
        report.line(
            f"  {_fmt_dt(e.received_at)} {e.event} {e.asaas_payment_id or '-'} "
            f"outcome={e.outcome or '-'} processado={'sim' if e.processed_at else 'não'}",
        )


def diagnose(report: Report, tenant: Tenant, *, client: SandboxAsaasClient | None = None) -> None:
    report.line(f"Ambiente: Asaas {urlparse(settings.ASAAS_API_URL).hostname} (sandbox), chave de sandbox.")
    report_tenant_state(report, tenant)
    report.line(
        "  dados do tenant: "
        f"usuarios={User.objects.filter(tenant_id=tenant.pk).count()} "
        f"mercados={_count('markets.Market', tenant)} "
        f"moradores={_count('residents.Resident', tenant)} "
        f"instancias_whatsapp={_count('integrations.WhatsappInstance', tenant)} "
        "(use só tenant fictício)",
    )

    sub = subscription_of(tenant)
    if sub is None:
        report.check("Assinatura local", False, "tenant sem Subscription")
        return
    report.line(
        f"Assinatura local: status={sub.status} customer={sub.asaas_customer_id} "
        f"subscription={sub.asaas_subscription_id}",
    )
    report_ledger(report, sub)

    client = client or SandboxAsaasClient()
    report.line("Sandbox Asaas:")
    try:
        customer = client.get_customer(sub.asaas_customer_id)
        report.check(
            "Cliente existe no sandbox atual",
            not customer.get("deleted"),
            f"{sub.asaas_customer_id} deleted={bool(customer.get('deleted'))}",
            source="SANDBOX",
        )
    except AsaasAPIError as exc:
        report.check("Cliente existe no sandbox atual", False, asaas_error_text(exc), source="SANDBOX")

    try:
        remote = client.get_subscription(sub.asaas_subscription_id)
    except AsaasAPIError as exc:
        report.check("Assinatura existe no sandbox atual", False, asaas_error_text(exc), source="SANDBOX")
        return
    same_customer = str(remote.get("customer") or "") == sub.asaas_customer_id
    report.check(
        "Assinatura existe no sandbox atual",
        not remote.get("deleted") and same_customer,
        f"{sub.asaas_subscription_id} status={remote.get('status')} billingType={remote.get('billingType')} "
        f"ciclo={remote.get('cycle')} proximo_venc={remote.get('nextDueDate')} valor={remote.get('value')} "
        f"deleted={bool(remote.get('deleted'))} mesmo_cliente={'sim' if same_customer else 'não'}",
        source="SANDBOX",
    )

    try:
        payments = _subscription_payments(client, sub)
    except AsaasAPIError as exc:
        report.check("Cobranças da assinatura no sandbox", False, asaas_error_text(exc), source="SANDBOX")
        return
    local = {c.asaas_payment_id: c for c in SubscriptionCharge.objects.filter(subscription=sub)}
    report.line(f"  Cobranças da assinatura no sandbox ({len(payments)}):")
    divergences: list[str] = []
    for p in payments:
        pid = str(p.get("id") or "")
        status = payment_status_of(p)
        charge = local.get(pid)
        local_flag = "ausente no ledger"
        if charge is not None:
            local_flag = "EXIGIDA" if charge.is_outstanding else ("paga" if charge.paid_at else "registrada")
        report.line(
            f"    {pid} venc={p.get('dueDate')} original={p.get('originalDueDate')} "
            f"valor={p.get('value')} status={status} local={local_flag}",
        )
        if status == "OVERDUE" and not (charge and charge.is_outstanding):
            divergences.append(f"{pid} está OVERDUE no Asaas mas não é exigida localmente (webhook não processado?)")
        if status in PAID_STATUSES and charge is not None and charge.is_outstanding:
            divergences.append(f"{pid} está paga no Asaas mas segue exigida localmente (webhook de pagamento pendente?)")
    eligible = [str(p.get("id")) for p in payments if payment_status_of(p) == "PENDING" and not p.get("deleted")]
    report.line(f"  Elegíveis para force-overdue (PENDING): {', '.join(eligible) or 'nenhuma'}")
    if not eligible:
        report.line("  " + PREPARE_CHARGE_HELP.replace("\n", "\n  "))
    report.line(f"  Divergências: {'; '.join(divergences) or 'nenhuma'}")

    try:
        hooks = client.list_webhooks()
    except AsaasAPIError as exc:
        report.check("Webhooks configurados no sandbox", False, asaas_error_text(exc), source="SANDBOX")
        return
    report.line(f"  Webhooks configurados no sandbox ({len(hooks)}):")
    for hook in hooks:
        events = hook.get("events") or []
        report.line(
            f"    nome={hook.get('name') or '-'} url={hook.get('url')} enabled={hook.get('enabled')} "
            f"interrupted={hook.get('interrupted')} sendType={hook.get('sendType') or '-'} "
            f"PAYMENT_OVERDUE={'sim' if 'PAYMENT_OVERDUE' in events else 'não'} "
            f"PAYMENT_CONFIRMED={'sim' if 'PAYMENT_CONFIRMED' in events else 'não'}",
        )
    usable = [h for h in hooks if h.get("enabled") and not h.get("interrupted")]
    report.check(
        "Há webhook ativo e sem fila interrompida",
        bool(usable),
        "confira se a URL aponta para o staging (/api/billing/webhooks/asaas/ ou /api/webhooks/asaas/)",
        source="SANDBOX",
    )


# --------------------------------------------------------------------------- ações no sandbox


def generate_charges(
    report: Report,
    tenant: Tenant,
    *,
    until: str,
    dry_run: bool,
    client: SandboxAsaasClient | None = None,
) -> None:
    sub = require_subscription(tenant)
    try:
        year_s, month_s = until.split("-", 1)
        year, month = int(year_s), int(month_s)
        target = date(year, month, 1)
    except (ValueError, TypeError) as exc:
        raise QaActionError("--until deve ser AAAA-MM.") from exc
    today = timezone.localdate()
    months_ahead = (target.year - today.year) * 12 + (target.month - today.month)
    if months_ahead < 0 or months_ahead > MAX_GENERATE_MONTHS_AHEAD:
        raise QaActionError(f"--until precisa estar entre o mês atual e {MAX_GENERATE_MONTHS_AHEAD} meses à frente.")

    client = client or SandboxAsaasClient()
    before = _subscription_payments(client, sub)
    report.line(f"Cobranças da assinatura antes: {len(before)}")
    if dry_run:
        report.line(
            f"[dry-run] chamaria GET /v3/subscriptions/{sub.asaas_subscription_id}/paymentBook"
            f"?month={month}&year={year} (sandbox).",
        )
        return
    book_error: AsaasAPIError | None = None
    size = 0
    try:
        size = client.generate_payment_book(sub.asaas_subscription_id, month=month, year=year)
    except AsaasAPIError as exc:
        book_error = exc
    # O sandbox pode criar as cobranças e ainda assim recusar o PDF (HTTP 400 "Nenhuma cobrança
    # encontrada"); o resultado vale pelo que existe na assinatura depois da chamada.
    after = _subscription_payments(client, sub)
    known = {p.get("id") for p in before}
    created = [p for p in after if p.get("id") not in known]
    if book_error is not None and not created:
        raise QaActionError(f"paymentBook recusado: {asaas_error_text(book_error)}") from book_error
    book_note = (
        f"paymentBook respondeu {asaas_error_text(book_error)}, mas as cobranças foram criadas"
        if book_error is not None
        else f"PDF de {size} bytes descartado"
    )
    report.check(
        "Cobranças futuras geradas na assinatura",
        bool(created),
        f"{book_note}; novas: "
        + (", ".join(f"{p.get('id')} venc={p.get('dueDate')} status={p.get('status')}" for p in created) or "nenhuma"),
        source="SANDBOX",
    )
    if not created:
        report.line(
            "  Sem cobranças novas: confira no painel do sandbox se a assinatura está ativa e se o mês "
            "informado é posterior à última cobrança existente.",
        )


def force_overdue(
    report: Report,
    tenant: Tenant,
    *,
    payment_id: str,
    dry_run: bool,
    wait: int,
    client: SandboxAsaasClient | None = None,
) -> None:
    sub = require_subscription(tenant)
    client = client or SandboxAsaasClient()
    if payment_id:
        payment = _require_payment_of_subscription(client, sub, payment_id)
        if payment_status_of(payment) != "PENDING":
            raise QaActionError(
                f"Cobrança {payment_id} está {payment_status_of(payment)}; só PENDING é elegível.\n"
                + PREPARE_CHARGE_HELP,
            )
    else:
        candidates = [
            p for p in _subscription_payments(client, sub) if payment_status_of(p) == "PENDING" and not p.get("deleted")
        ]
        if not candidates:
            raise QaActionError(PREPARE_CHARGE_HELP)
        payment = candidates[0]
    pid = str(payment.get("id"))
    report.line(
        f"Cobrança escolhida: {pid} venc={payment.get('dueDate')} valor={payment.get('value')} "
        f"status={payment_status_of(payment)} assinatura={sub.asaas_subscription_id}",
    )
    if dry_run:
        report.line(f"[dry-run] chamaria POST /v3/sandbox/payment/{pid}/overdue e aguardaria PAYMENT_OVERDUE.")
        return
    started = timezone.now()
    try:
        result = client.force_overdue(pid)
    except AsaasAPIError as exc:
        raise QaActionError(f"Sandbox recusou forçar o vencimento: {asaas_error_text(exc)}") from exc
    report.check(
        "Vencimento forçado no sandbox",
        payment_status_of(result) in ("", "OVERDUE"),
        f"{pid} status={payment_status_of(result) or '(sem corpo)'}",
        source="SANDBOX",
    )
    if wait > 0:
        wait_for_webhook(report, payment_id=pid, events=OVERDUE_EVENTS, since=started, timeout=wait)
        report_tenant_state(report, tenant)
    else:
        report.line("Sem --wait: rode diagnose para ver se o PAYMENT_OVERDUE chegou.")


def confirm_payment(
    report: Report,
    tenant: Tenant,
    *,
    payment_id: str,
    dry_run: bool,
    wait: int,
    client: SandboxAsaasClient | None = None,
) -> None:
    if not payment_id:
        raise QaActionError("confirm-payment exige --payment-id (uma cobrança exigida da assinatura).")
    sub = require_subscription(tenant)
    client = client or SandboxAsaasClient()
    payment = _require_payment_of_subscription(client, sub, payment_id)
    status = payment_status_of(payment)
    if status not in ("PENDING", "OVERDUE"):
        raise QaActionError(f"Cobrança {payment_id} está {status}; só PENDING/OVERDUE podem ser confirmadas.")
    remaining = [c.asaas_payment_id for c in outstanding_charges(sub) if c.asaas_payment_id != payment_id]
    report.line(
        f"Cobrança: {payment_id} venc={payment.get('dueDate')} status={status}; "
        f"outras exigidas que continuarão em aberto: {', '.join(remaining) or 'nenhuma'}",
    )
    if dry_run:
        report.line(f"[dry-run] chamaria POST /v3/sandbox/payment/{payment_id}/confirm e aguardaria PAYMENT_CONFIRMED.")
        return
    started = timezone.now()
    try:
        result = client.confirm_payment(payment_id)
    except AsaasAPIError as exc:
        raise QaActionError(f"Sandbox recusou confirmar o pagamento: {asaas_error_text(exc)}") from exc
    report.check(
        "Pagamento confirmado no sandbox",
        payment_status_of(result) in ("",) + tuple(PAID_STATUSES),
        f"{payment_id} status={payment_status_of(result) or '(sem corpo)'}",
        source="SANDBOX",
    )
    if wait > 0:
        wait_for_webhook(report, payment_id=payment_id, events=PAID_EVENTS, since=started, timeout=wait)
        report_tenant_state(report, tenant)
    else:
        report.line("Sem --wait: rode diagnose para ver se o PAYMENT_CONFIRMED chegou.")


# --------------------------------------------------------------------------- carência e restauração


def advance_grace(report: Report, tenant: Tenant, *, ends_in_minutes: int, dry_run: bool) -> QaBillingSnapshot | None:
    """
    Antecipa o fim da carência só deste tenant, deslocando overdue_since (e o overdue_at das
    cobranças exigidas, pelo mesmo intervalo) para que billing_rules.grace_deadline() caia em
    agora + ends_in_minutes. Não mexe em relógio, BILLING_GRACE_DAYS nem no status.
    """
    if ends_in_minutes < 0:
        raise QaActionError("--ends-in-minutes não pode ser negativo.")
    sub = require_subscription(tenant)
    tenant.refresh_from_db()
    if tenant.subscription_status != Tenant.SubscriptionStatus.OVERDUE or tenant.overdue_since is None:
        raise QaActionError(
            f"Tenant está {tenant.subscription_status}; antecipar a carência exige OVERDUE com overdue_since "
            "(force-overdue + webhook primeiro).",
        )
    required = list(outstanding_charges(sub))
    if not required:
        raise QaActionError(
            "Nenhuma cobrança exigida no ledger: a inadimplência precisa vir de uma cobrança real "
            "da assinatura (force-overdue + webhook).",
        )
    now = timezone.now()
    current_deadline = grace_deadline(tenant.overdue_since)
    target_deadline = now + timedelta(minutes=ends_in_minutes)
    if target_deadline >= current_deadline:
        raise QaActionError(
            f"A carência já termina em {_fmt_dt(current_deadline)}; o novo fim ({_fmt_dt(target_deadline)}) "
            "não é uma antecipação.",
        )
    shift = target_deadline - current_deadline
    report.line(
        f"Fim da carência: {_fmt_dt(current_deadline)} → {_fmt_dt(target_deadline)} "
        f"(overdue_since {_fmt_dt(tenant.overdue_since)} → {_fmt_dt(tenant.overdue_since + shift)})",
    )
    for charge in required:
        report.line(
            f"  {charge.asaas_payment_id}: exigida_em {_fmt_dt(charge.overdue_at)} → "
            f"{_fmt_dt(charge.overdue_at + shift)}",
        )
    if dry_run:
        report.line("[dry-run] nada foi alterado.")
        return None

    with transaction.atomic():
        locked = Tenant.objects.select_for_update().get(pk=tenant.pk)
        snapshot = QaBillingSnapshot.objects.create(
            tenant=locked,
            action="advance-grace",
            data=capture_state(locked, sub),
        )
        locked.overdue_since = locked.overdue_since + shift
        locked.save(update_fields=["overdue_since", "updated_at"])
        for charge in SubscriptionCharge.objects.select_for_update().filter(pk__in=[c.pk for c in required]):
            charge.overdue_at = charge.overdue_at + shift
            charge.save(update_fields=["overdue_at", "updated_at"])

    tenant.refresh_from_db()
    report.check(
        "Carência antecipada (billing_rules)",
        grace_deadline(tenant.overdue_since) == target_deadline,
        f"fim={_fmt_dt(tenant.grace_ends_at())}; status segue {tenant.subscription_status}; snapshot={snapshot.pk}",
    )
    report.line("Suspensão: rode run-check (check_subscriptions) — o status não foi alterado aqui.")
    return snapshot


def restore(report: Report, tenant: Tenant, *, snapshot_id: int | None, dry_run: bool) -> None:
    qs = QaBillingSnapshot.objects.filter(tenant=tenant, restored_at__isnull=True)
    snapshot = qs.filter(pk=snapshot_id).first() if snapshot_id else qs.first()
    if snapshot is None:
        raise QaActionError("Nenhum snapshot pendente de restauração para este tenant.")
    data = snapshot.data
    sub = subscription_of(tenant)
    current = capture_state(tenant, sub)

    now_paid = {c["asaas_payment_id"] for c in current["charges"] if c["paid_at"] or c["removed_at"]}
    was_open = {
        c["asaas_payment_id"] for c in data.get("charges", []) if not c.get("paid_at") and not c.get("removed_at")
    }
    settled = sorted(now_paid & was_open)
    if settled:
        raise QaActionError(
            "Cobranças quitadas/removidas depois do snapshot "
            f"({', '.join(settled)}): restaurar criaria estado sem vínculo com o ledger. "
            "Recomece o cenário com uma nova cobrança.",
        )

    diffs = _state_diff(current, data)
    report.line(f"Snapshot {snapshot.pk} ({snapshot.action}, {_fmt_dt(snapshot.created_at)}):")
    for line in diffs or ["nada a restaurar (estado igual ao snapshot)"]:
        report.line(f"  {line}")
    if dry_run:
        report.line("[dry-run] nada foi alterado.")
        return

    with transaction.atomic():
        locked = Tenant.objects.select_for_update().get(pk=tenant.pk)
        for name in TENANT_SNAPSHOT_FIELDS:
            setattr(locked, name, _deserialize(name, data["tenant"].get(name)))
        locked.save(update_fields=[*TENANT_SNAPSHOT_FIELDS, "updated_at"])
        sub_data = data.get("subscription")
        if sub_data:
            Subscription.objects.filter(pk=sub_data["id"]).update(status=sub_data["status"], updated_at=timezone.now())
        for charge_data in data.get("charges", []):
            SubscriptionCharge.objects.filter(pk=charge_data["id"]).update(
                overdue_at=_deserialize("overdue_at", charge_data.get("overdue_at")),
                updated_at=timezone.now(),
            )
        snapshot.restored_at = timezone.now()
        snapshot.save(update_fields=["restored_at"])

    remaining = _state_diff(capture_state(tenant, sub), data)
    report.check("Cenário restaurado", not remaining, "; ".join(remaining) or f"snapshot={snapshot.pk}")
    report.line(
        "  Não revertido: estado das cobranças no sandbox Asaas e o logout Evolution já executado "
        "(reconecte pelo QR Code).",
    )


# --------------------------------------------------------------------------- check_subscriptions


def run_check(
    report: Report,
    tenant: Tenant,
    *,
    dry_run: bool,
    simulate_logout_failure: bool,
    stdout,
    stderr,
) -> None:
    kwargs = {"tenant_id": tenant.pk, "dry_run": dry_run, "stdout": stdout, "stderr": stderr}
    if simulate_logout_failure and not dry_run:
        report.line("[SIMULADO] logout Evolution vai falhar nesta execução (RuntimeError de QA).")
        with mock.patch(
            "apps.billing.services.subscription_enforcement.logout_tenant_whatsapp_sessions",
            side_effect=RuntimeError("QA: falha simulada do logout Evolution"),
        ):
            call_command("check_subscriptions", **kwargs)
    else:
        call_command("check_subscriptions", **kwargs)
    report_tenant_state(report, tenant)


# --------------------------------------------------------------------------- validação


class _GateAllowed(Exception):
    pass


def probe_bot_gate(tenant: Tenant) -> bool:
    """
    Entrega uma mensagem sintética ao fluxo real de entrada (parser + handler da Evolution).
    Para logo após a verificação de acesso: nada é respondido ao WhatsApp e o banco é revertido.
    """
    from apps.billing.services import tenant_suspension
    from apps.integrations.models import WhatsappInstance
    from apps.integrations.services.webhook_handlers import handle_evolution_webhook
    from apps.integrations.services.webhook_parser import parse_evolution_payload

    instance = (
        WhatsappInstance.all_objects.filter(tenant_id=tenant.pk, is_active=True).order_by("-pk").first()
        or WhatsappInstance(tenant_id=tenant.pk, instance_name=f"qa-probe-{tenant.pk}")
    )
    event = parse_evolution_payload(
        {
            "event": "MESSAGE",
            "instance": instance.instance_name,
            "data": {
                "key": {"remoteJid": PROBE_JID, "id": f"qa-probe-{uuid.uuid4().hex}", "fromMe": False},
                "message": {"conversation": "QA: verificação de acesso do bot"},
            },
        },
    )
    if event is None:
        raise QaActionError("Parser da Evolution não reconheceu a mensagem sintética.")

    original = tenant_suspension.tenant_has_messaging_access
    seen: dict[str, bool] = {}

    def spy(tenant_id: int) -> bool:
        seen["allowed"] = original(tenant_id)
        if seen["allowed"]:
            raise _GateAllowed
        return False

    with rolled_back(), mock.patch.object(tenant_suspension, "tenant_has_messaging_access", spy):
        try:
            handle_evolution_webhook(event, instance)
        except _GateAllowed:
            pass
    if "allowed" not in seen:
        raise QaActionError("A mensagem sintética não chegou à verificação de acesso do bot.")
    return seen["allowed"]


def _request_host() -> str:
    for host in getattr(settings, "ALLOWED_HOSTS", None) or []:
        host = str(host).strip()
        if host and host != "*" and not host.startswith("."):
            return host
    return "localhost"


def _api_client(tenant: Tenant) -> Client | None:
    from apps.accounts.serializers import TenantTokenObtainPairSerializer

    user = (
        User.objects.filter(tenant_id=tenant.pk, is_tenant_admin=True, is_active=True).order_by("pk").first()
    )
    if user is None:
        return None
    token = TenantTokenObtainPairSerializer.get_token(user).access_token
    return Client(
        raise_request_exception=False,
        HTTP_HOST=_request_host(),
        HTTP_X_FORWARDED_PROTO="https",
        HTTP_AUTHORIZATION=f"Bearer {token}",
    )


def _call(client: Client, method: str, path: str, **kwargs) -> tuple[int, dict[str, Any]]:
    with rolled_back():
        response = getattr(client, method)(path, **kwargs)
    try:
        body = response.json()
    except ValueError:
        body = {}
    return response.status_code, body if isinstance(body, dict) else {}


def _bot_check(report: Report, name: str, *, allowed: bool, expected: bool) -> None:
    report.check(
        name,
        allowed is expected,
        "mensagem seguiria para o bot" if allowed else "mensagem ignorada (tenant sem acesso)",
        source="SIMULADO",
    )


def validate(
    report: Report,
    tenant: Tenant,
    *,
    expect: str,
    control_tenant: Tenant | None = None,
) -> None:
    report_tenant_state(report, tenant)
    tenant.refresh_from_db()
    sub = subscription_of(tenant)
    required = list(outstanding_charges(sub)) if sub else []
    report.line(f"Cobranças exigidas: {', '.join(c.asaas_payment_id for c in required) or 'nenhuma'}")
    report.line(f"Verificações (esperado: {expect}); HTTP in-process com o middleware real, escritas revertidas:")

    client = _api_client(tenant)
    if client is None:
        report.check("Usuário admin do tenant", False, "sem admin ativo para gerar o JWT")
        return

    now = timezone.now()
    status = tenant.subscription_status
    blocked = status == Tenant.SubscriptionStatus.SUSPENDED or tenant.billing_blocked_at is not None
    protected_code, protected_body = _call(client, "get", PROTECTED_PATH)
    me_code, me_body = _call(client, "get", ME_PATH)
    bot_allowed = probe_bot_gate(tenant)

    if expect == "grace":
        grace_end = tenant.grace_ends_at()
        report.check("Status OVERDUE", status == Tenant.SubscriptionStatus.OVERDUE, status)
        report.check("Dentro da carência", bool(grace_end and now < grace_end), f"fim={_fmt_dt(grace_end)}")
        report.check("Há cobrança exigida", bool(required), f"{len(required)}")
        report.check(f"Painel liberado (GET {PROTECTED_PATH})", protected_code == 200, f"HTTP {protected_code}")
        report.check(
            f"Próprio estado com fim da carência (GET {ME_PATH})",
            me_code == 200 and bool(me_body.get("grace_ends_at")),
            f"HTTP {me_code} grace_ends_at={me_body.get('grace_ends_at')}",
        )
        _bot_check(report, "Bot responde (fluxo de entrada)", allowed=bot_allowed, expected=True)

    elif expect == "blocked":
        report.check(
            "Tenant bloqueado",
            blocked,
            f"status={status} billing_blocked_at={_fmt_dt(tenant.billing_blocked_at)}",
        )
        report.check("Há cobrança exigida", bool(required), f"{len(required)}")
        report.check(
            f"API protegida retorna 402 (GET {PROTECTED_PATH})",
            protected_code == 402 and protected_body.get("error") == "billing_suspended",
            f"HTTP {protected_code} error={protected_body.get('error')}",
        )
        report.check(
            f"Próprio estado acessível (GET {ME_PATH})",
            me_code == 200
            and bool(me_body.get("billing_blocked") or me_body.get("subscription_status") == "SUSPENDED"),
            f"HTTP {me_code} status={me_body.get('subscription_status')} "
            f"motivo={me_body.get('billing_block_reason')}",
        )
        summary_code, summary_body = _call(client, "get", PAYMENT_SUMMARY_PATH)
        report.check(
            f"Resumo de cobrança acessível (GET {PAYMENT_SUMMARY_PATH})",
            summary_code != 402,
            f"HTTP {summary_code} faturas_exigidas={len(summary_body.get('required_charges') or [])}",
        )
        regularize_code, _ = _call(client, "get", REGULARIZE_PATH)
        report.check(
            f"Regularização não é barrada pelo bloqueio ({REGULARIZE_PATH})",
            regularize_code != 402,
            f"GET → HTTP {regularize_code} (405 = rota alcançável, só aceita POST)",
        )
        anonymous = Client(raise_request_exception=False, HTTP_HOST=_request_host())
        login_code, _ = _call(anonymous, "post", LOGIN_PATH, data={})
        report.check(
            f"Login não é barrado pelo bloqueio (POST {LOGIN_PATH})",
            login_code != 402,
            f"HTTP {login_code} com corpo vazio (400 = rota alcançável)",
        )
        _bot_check(report, "Bot não responde (fluxo de entrada)", allowed=bot_allowed, expected=False)
        report.line(
            f"  Logout Evolution: pendente_desde={_fmt_dt(tenant.whatsapp_logout_pending_since)} "
            f"tentativas={tenant.whatsapp_logout_attempts} ultimo_erro={tenant.whatsapp_logout_last_error or '-'} "
            "(o bot fica bloqueado mesmo com o logout pendente)",
        )

    elif expect == "active":
        report.check("Status ACTIVE", status == Tenant.SubscriptionStatus.ACTIVE, status)
        report.check("Sem bloqueio local", tenant.billing_blocked_at is None, _fmt_dt(tenant.billing_blocked_at))
        report.check(
            "Nenhuma cobrança exigida",
            not required,
            ", ".join(c.asaas_payment_id for c in required) or "-",
        )
        report.check(f"Painel liberado (GET {PROTECTED_PATH})", protected_code == 200, f"HTTP {protected_code}")
        _bot_check(report, "Bot responde (fluxo de entrada)", allowed=bot_allowed, expected=True)
        report.check(
            "Sem logout Evolution pendente",
            tenant.whatsapp_logout_pending_since is None,
            _fmt_dt(tenant.whatsapp_logout_pending_since),
        )
    else:
        raise QaActionError(f"--expect inválido: {expect}")

    if control_tenant is not None:
        report.line(f"Tenant de controle {control_tenant.pk} ({control_tenant.slug}):")
        control_client = _api_client(control_tenant)
        if control_client is None:
            report.check("Tenant de controle funcionando", False, "sem admin ativo")
            return
        code, _ = _call(control_client, "get", PROTECTED_PATH)
        report.check(f"Controle: painel liberado (GET {PROTECTED_PATH})", code == 200, f"HTTP {code}")
        _bot_check(report, "Controle: bot responde", allowed=probe_bot_gate(control_tenant), expected=True)


# --------------------------------------------------------------------------- webhook duplicado/antigo


def replay_webhook(
    report: Report,
    tenant: Tenant,
    *,
    mode: str,
    payment_id: str,
    client: SandboxAsaasClient | None = None,
) -> None:
    """
    Reentrega in-process um webhook duplicado ou antigo, montado com a cobrança real do
    sandbox, e compara o estado antes/depois. Tudo é revertido ao final.
    """
    from apps.billing.services.webhook_processor import process_asaas_webhook_payload

    sub = require_subscription(tenant)
    client = client or SandboxAsaasClient()
    payloads: list[dict[str, Any]] = []

    if mode == "duplicate":
        qs = AsaasWebhookEvent.objects.filter(
            asaas_subscription_id=sub.asaas_subscription_id,
            processed_at__isnull=False,
        ).exclude(event_key__startswith="sha256:")
        if payment_id:
            qs = qs.filter(asaas_payment_id=payment_id)
        record = qs.order_by("-received_at").first()
        if record is None or not record.asaas_payment_id:
            raise QaActionError("Nenhum webhook real processado desta assinatura para duplicar.")
        payment = client.get_payment(record.asaas_payment_id)
        payloads.append(
            {
                "id": record.event_key,
                "event": record.event,
                "dateCreated": _asaas_datetime(record.event_created_at or record.received_at),
                "payment": payment,
            },
        )
        report.line(f"Duplicata de {record.event} {record.asaas_payment_id} (mesmo id de evento {record.event_key}).")
    elif mode == "stale":
        charges = SubscriptionCharge.objects.filter(subscription=sub, paid_at__isnull=False)
        if payment_id:
            charges = charges.filter(asaas_payment_id=payment_id)
        charge = charges.order_by("paid_at").first()
        if charge is None:
            raise QaActionError("Nenhuma cobrança paga desta assinatura para reenviar como evento antigo.")
        payment = client.get_payment(charge.asaas_payment_id)
        older = _asaas_datetime(charge.paid_at - timedelta(days=1))
        payloads.append(
            {
                "id": f"evt_qa_{uuid.uuid4().hex}",
                "event": "PAYMENT_OVERDUE",
                "dateCreated": older,
                "payment": {**payment, "status": "OVERDUE"},
            },
        )
        payloads.append(
            {
                "id": f"evt_qa_{uuid.uuid4().hex}",
                "event": "PAYMENT_CONFIRMED",
                "dateCreated": older,
                "payment": payment,
            },
        )
        report.line(
            f"Eventos antigos (novos ids) da cobrança já paga {charge.asaas_payment_id}: "
            "PAYMENT_OVERDUE atrasado e PAYMENT_CONFIRMED repetido.",
        )
    else:
        raise QaActionError(f"--mode inválido: {mode}")

    with rolled_back(), mock.patch("apps.billing.services.webhook_processor.schedule_meta_purchase_event"):
        before = capture_state(tenant, sub)
        for payload in payloads:
            process_asaas_webhook_payload(payload)
            key = payload["id"]
            outcome = AsaasWebhookEvent.objects.filter(event_key=key).values_list("outcome", flat=True).first()
            report.line(f"  {payload['event']} → outcome={outcome or '-'}")
        diffs = _state_diff(before, capture_state(tenant, sub))
    report.check(
        "Estado do tenant e do ledger inalterado",
        not diffs,
        "; ".join(diffs) or "sem mudanças (reprocessamento revertido)",
        source="SIMULADO",
    )

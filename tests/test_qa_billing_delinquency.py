"""Comando de QA qa_billing_delinquency (staging + Asaas sandbox)."""

from __future__ import annotations

import socket
import uuid
from datetime import date, timedelta
from io import StringIO
from unittest import mock

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.utils import timezone

from apps.billing.models import QaBillingSnapshot, Subscription, SubscriptionCharge
from apps.billing.services import qa_delinquency as qa
from apps.billing.services.asaas_client import AsaasAPIError
from apps.billing.services.webhook_processor import process_asaas_webhook_payload
from apps.residents.models import ChatSession
from apps.tenants.billing_rules import grace_deadline
from apps.tenants.models import Tenant
from tests.factories import SubscriptionFactory, TenantFactory, UserFactory, WhatsappInstanceFactory

CLIENT_PATH = "apps.billing.services.qa_delinquency.SandboxAsaasClient"
LOGOUT_SESSION_PATH = "apps.billing.services.subscription_enforcement.logout_whatsapp_session"
SUMMARY_CLIENT_PATH = "apps.billing.services.payment_method.AsaasClient"
PURCHASE_PATH = "apps.billing.services.webhook_processor.schedule_meta_purchase_event"


@pytest.fixture(autouse=True)
def no_external_calls(monkeypatch):
    """
    Meta CAPI mockada e rede de saída bloqueada. As tentativas são registradas e
    reprovam o teste mesmo quando o código chamador engole a exceção.
    """
    attempts: list[str] = []
    real_connect = socket.socket.connect
    real_connect_ex = socket.socket.connect_ex

    def refuse(target) -> None:
        attempts.append(repr(target))
        raise ConnectionRefusedError(f"Chamada externa não prevista no teste: {target!r}")

    def guarded_connect(sock, address):
        if sock.family == getattr(socket, "AF_UNIX", None):
            return real_connect(sock, address)
        refuse(address)

    def guarded_connect_ex(sock, address):
        if sock.family == getattr(socket, "AF_UNIX", None):
            return real_connect_ex(sock, address)
        refuse(address)

    def guarded_getaddrinfo(host, *args, **kwargs):
        refuse(host)

    monkeypatch.setattr(socket.socket, "connect", guarded_connect)
    monkeypatch.setattr(socket.socket, "connect_ex", guarded_connect_ex)
    monkeypatch.setattr(socket, "getaddrinfo", guarded_getaddrinfo)
    with mock.patch(PURCHASE_PATH) as purchase:
        yield purchase
    assert not attempts, f"Chamadas externas não previstas: {attempts}"


@pytest.fixture
def summary_client():
    """Resumo de pagamento com resposta real de assinatura (nunca um MagicMock serializado)."""
    with mock.patch(SUMMARY_CLIENT_PATH) as client_cls:
        client_cls.return_value.get_subscription.return_value = {
            "billingType": "CREDIT_CARD",
            "status": "ACTIVE",
            "nextDueDate": timezone.localdate().isoformat(),
            "creditCardBrand": "VISA",
            "creditCardNumber": "4242",
        }
        yield client_cls


@pytest.fixture(autouse=True)
def sandbox_settings(settings):
    settings.ASAAS_API_URL = "https://api-sandbox.asaas.com/v3"
    settings.ASAAS_API_KEY = "$aact_hmlg_qa-test"
    settings.ALLOWED_HOSTS = ["staging-app.marketchat.com.br", "localhost", "testserver"]
    settings.CSRF_TRUSTED_ORIGINS = ["https://staging-app.marketchat.com.br"]
    settings.CORS_ALLOWED_ORIGINS = ["https://staging-app.marketchat.com.br"]
    settings.PUBLIC_WEBHOOK_BASE_URL = "http://192.168.1.23:8001"
    settings.FRONTEND_APP_ORIGIN = "https://staging-app.marketchat.com.br"
    return settings


def _payment(sub: Subscription, pid: str, *, status: str = "PENDING", due: date | None = None) -> dict:
    due = due or timezone.localdate() + timedelta(days=5)
    return {
        "object": "payment",
        "id": pid,
        "customer": sub.asaas_customer_id,
        "subscription": sub.asaas_subscription_id,
        "dueDate": due.isoformat(),
        "originalDueDate": due.isoformat(),
        "value": 59.9,
        "billingType": "CREDIT_CARD",
        "status": status,
        "deleted": False,
    }


def _deliver(event: str, payment: dict) -> None:
    """Entrega como o Asaas faria (envelope documentado) ao processador real do staging."""
    process_asaas_webhook_payload(
        {
            "id": f"evt_{uuid.uuid4().hex}&{uuid.uuid4().int % 10**9}",
            "event": event,
            "dateCreated": timezone.localtime().strftime("%Y-%m-%d %H:%M:%S"),
            "payment": payment,
        },
    )


class FakeSandbox:
    """Sandbox Asaas em memória; force/confirm disparam o webhook como o Asaas faria."""

    def __init__(self, sub: Subscription, payments: list[dict], *, deliver: bool = True):
        self.sub = sub
        self.payments = {p["id"]: dict(p) for p in payments}
        self.deliver = deliver
        self.calls: list[tuple[str, str]] = []

    def list_subscription_payments(self, subscription_id, **params):
        return [dict(p) for p in self.payments.values() if p["subscription"] == subscription_id]

    def get_payment(self, payment_id):
        if payment_id not in self.payments:
            raise AsaasAPIError("not found", status_code=404, payload={"errors": [{"description": "não encontrada"}]})
        return dict(self.payments[payment_id])

    def force_overdue(self, payment_id):
        self.calls.append(("overdue", payment_id))
        self.payments[payment_id]["status"] = "OVERDUE"
        if self.deliver:
            _deliver("PAYMENT_OVERDUE", dict(self.payments[payment_id]))
        return dict(self.payments[payment_id])

    def confirm_payment(self, payment_id):
        self.calls.append(("confirm", payment_id))
        self.payments[payment_id]["status"] = "CONFIRMED"
        if self.deliver:
            _deliver("PAYMENT_CONFIRMED", dict(self.payments[payment_id]))
        return dict(self.payments[payment_id])

    def generate_payment_book(self, subscription_id, *, month, year):
        self.calls.append(("paymentBook", f"{year}-{month:02d}"))
        pid = f"pay_book_{year}{month:02d}"
        self.payments[pid] = _payment(self.sub, pid, due=date(year, month, 10))
        return 1234

    def get_customer(self, customer_id):
        return {"id": customer_id, "deleted": False}

    def get_subscription(self, subscription_id):
        return {
            "id": subscription_id,
            "customer": self.sub.asaas_customer_id,
            "status": "ACTIVE",
            "billingType": "CREDIT_CARD",
            "cycle": "MONTHLY",
            "nextDueDate": timezone.localdate().isoformat(),
            "value": 59.9,
            "deleted": False,
        }

    def list_webhooks(self):
        return [
            {
                "name": "staging",
                "url": "https://staging-api.marketchat.com.br/api/billing/webhooks/asaas/",
                "enabled": True,
                "interrupted": False,
                "sendType": "SEQUENTIALLY",
                "events": ["PAYMENT_OVERDUE", "PAYMENT_CONFIRMED"],
            },
        ]


def _qa_tenant(**kwargs):
    defaults = {
        "slug": f"qa-inadimplencia-{uuid.uuid4().hex[:6]}",
        "trial_started_at": timezone.now() - timedelta(days=60),
        "trial_ends_at": timezone.now() - timedelta(days=53),
        "subscription_status": Tenant.SubscriptionStatus.ACTIVE,
    }
    defaults.update(kwargs)
    tenant = TenantFactory(**defaults)
    sub = SubscriptionFactory(tenant=tenant, status=Subscription.Status.ACTIVE)
    UserFactory(tenant=tenant)
    return tenant, sub


def _run(*args, **options) -> str:
    out = StringIO()
    call_command("qa_billing_delinquency", *args, stdout=out, stderr=StringIO(), **options)
    return out.getvalue()


def _overdue_via_sandbox(tenant, sub, *pids: str) -> FakeSandbox:
    fake = FakeSandbox(sub, [_payment(sub, pid) for pid in pids])
    with mock.patch(CLIENT_PATH, return_value=fake):
        for pid in pids:
            _run("force-overdue", tenant_id=tenant.pk, confirm_slug=tenant.slug, payment_id=pid, wait=1)
    return fake


# --------------------------------------------------------------------------- guardas


@pytest.mark.parametrize(
    ("setting", "value", "message"),
    [
        ("ASAAS_API_URL", "https://api.asaas.com/v3", "fora do sandbox"),
        ("ASAAS_API_URL", "http://api-sandbox.asaas.com/v3", "fora do sandbox"),
        ("ASAAS_API_KEY", "$aact_prod_abc", "chave de produção"),
        ("ASAAS_API_KEY", "", "prefixo de sandbox"),
        ("ALLOWED_HOSTS", ["app.marketchat.com.br", "localhost"], "host de produção"),
        ("PUBLIC_WEBHOOK_BASE_URL", "https://app.marketchat.com.br", "host de produção"),
    ],
)
@pytest.mark.django_db
def test_refuses_production_or_non_sandbox_asaas(settings, setting, value, message):
    tenant, _ = _qa_tenant()
    setattr(settings, setting, value)

    with mock.patch(CLIENT_PATH) as client_cls, pytest.raises(CommandError, match=message):
        _run("diagnose", tenant_id=tenant.pk)

    client_cls.assert_not_called()


def test_sandbox_client_refuses_other_base_url(settings):
    settings.ASAAS_API_URL = "https://api.asaas.com/v3"
    with pytest.raises(qa.QaEnvironmentError):
        qa.SandboxAsaasClient()


@pytest.mark.django_db
def test_tenant_id_is_required():
    with pytest.raises(CommandError, match="--tenant-id"):
        _run("diagnose")


@pytest.mark.django_db
def test_mutating_action_requires_matching_slug():
    tenant, sub = _qa_tenant()
    fake = FakeSandbox(sub, [_payment(sub, "pay_a")])

    with mock.patch(CLIENT_PATH, return_value=fake), pytest.raises(CommandError, match="--confirm-slug"):
        _run("force-overdue", tenant_id=tenant.pk, confirm_slug="outro-tenant")

    assert fake.calls == []


# --------------------------------------------------------------------------- diagnose / sandbox


@pytest.mark.django_db
def test_diagnose_confirms_sandbox_objects_and_lists_eligible_charge():
    tenant, sub = _qa_tenant()
    fake = FakeSandbox(sub, [_payment(sub, "pay_a"), _payment(sub, "pay_paid", status="CONFIRMED")])

    with mock.patch(CLIENT_PATH, return_value=fake):
        output = _run("diagnose", tenant_id=tenant.pk)

    assert "[OK   ] [SANDBOX] Cliente existe no sandbox atual" in output
    assert "[OK   ] [SANDBOX] Assinatura existe no sandbox atual" in output
    assert "Elegíveis para force-overdue (PENDING): pay_a" in output
    assert "fim da carência=-" in output
    assert fake.calls == []


@pytest.mark.django_db
def test_diagnose_fails_when_subscription_missing_in_current_sandbox():
    tenant, sub = _qa_tenant()
    fake = FakeSandbox(sub, [])
    fake.get_subscription = mock.Mock(side_effect=AsaasAPIError("x", status_code=404))

    with mock.patch(CLIENT_PATH, return_value=fake), pytest.raises(CommandError, match="falharam"):
        _run("diagnose", tenant_id=tenant.pk)


@pytest.mark.django_db
def test_force_overdue_without_eligible_charge_explains_preparation():
    tenant, sub = _qa_tenant()
    fake = FakeSandbox(sub, [_payment(sub, "pay_paid", status="CONFIRMED")])

    with mock.patch(CLIENT_PATH, return_value=fake), pytest.raises(CommandError, match="generate-charges"):
        _run("force-overdue", tenant_id=tenant.pk, confirm_slug=tenant.slug)

    assert fake.calls == []


@pytest.mark.django_db
def test_force_overdue_refuses_charge_of_another_subscription():
    tenant, sub = _qa_tenant()
    _, other_sub = _qa_tenant()
    fake = FakeSandbox(sub, [_payment(other_sub, "pay_other")])

    with mock.patch(CLIENT_PATH, return_value=fake), pytest.raises(CommandError, match="não pertence"):
        _run("force-overdue", tenant_id=tenant.pk, confirm_slug=tenant.slug, payment_id="pay_other")

    assert fake.calls == []


@pytest.mark.django_db
def test_force_overdue_dry_run_calls_nothing():
    tenant, sub = _qa_tenant()
    fake = FakeSandbox(sub, [_payment(sub, "pay_a")])

    with mock.patch(CLIENT_PATH, return_value=fake):
        output = _run("force-overdue", tenant_id=tenant.pk, confirm_slug=tenant.slug, dry_run=True)

    assert "[dry-run] chamaria POST /v3/sandbox/payment/pay_a/overdue" in output
    assert fake.calls == []
    tenant.refresh_from_db()
    assert tenant.subscription_status == Tenant.SubscriptionStatus.ACTIVE


@pytest.mark.django_db
def test_force_overdue_waits_for_real_webhook_and_enters_grace():
    tenant, sub = _qa_tenant()
    fake = FakeSandbox(sub, [_payment(sub, "pay_a")])

    with mock.patch(CLIENT_PATH, return_value=fake):
        output = _run("force-overdue", tenant_id=tenant.pk, confirm_slug=tenant.slug, wait=1)

    assert fake.calls == [("overdue", "pay_a")]
    assert "[OK   ] [SANDBOX] Webhook real recebido e processado: PAYMENT_OVERDUE outcome=marked_overdue" in output
    tenant.refresh_from_db()
    assert tenant.subscription_status == Tenant.SubscriptionStatus.OVERDUE
    assert tenant.is_in_grace_period()
    assert SubscriptionCharge.objects.get(asaas_payment_id="pay_a").is_outstanding


@pytest.mark.django_db
def test_force_overdue_without_webhook_leaves_tenant_untouched():
    tenant, sub = _qa_tenant()
    fake = FakeSandbox(sub, [_payment(sub, "pay_a")], deliver=False)

    with mock.patch(CLIENT_PATH, return_value=fake):
        output = _run("force-overdue", tenant_id=tenant.pk, confirm_slug=tenant.slug)

    assert "Sem --wait" in output
    tenant.refresh_from_db()
    assert tenant.subscription_status == Tenant.SubscriptionStatus.ACTIVE


@pytest.mark.django_db
def test_wait_for_webhook_reports_timeout():
    report = qa.Report(write=lambda _line: None)

    record = qa.wait_for_webhook(
        report,
        payment_id="pay_missing",
        events=qa.OVERDUE_EVENTS,
        since=timezone.now(),
        timeout=0,
    )

    assert record is None
    assert [c.ok for c in report.checks] == [False]


@pytest.mark.django_db
def test_generate_charges_uses_subscription_payment_book():
    tenant, sub = _qa_tenant()
    fake = FakeSandbox(sub, [])
    target = timezone.localdate().replace(day=1) + timedelta(days=40)
    until = f"{target.year}-{target.month:02d}"

    with mock.patch(CLIENT_PATH, return_value=fake):
        output = _run("generate-charges", tenant_id=tenant.pk, confirm_slug=tenant.slug, until=until)

    assert fake.calls == [("paymentBook", until)]
    assert "[OK   ] [SANDBOX] Cobranças futuras geradas na assinatura" in output


def _book_refused(fake: FakeSandbox, *, creates: bool):
    real_book = fake.generate_payment_book

    def book(subscription_id, *, month, year):
        if creates:
            real_book(subscription_id, month=month, year=year)
        raise AsaasAPIError(
            "Erro na API Asaas",
            status_code=400,
            payload={"errors": [{"description": "Nenhuma cobrança encontrada para os filtros selecionados."}]},
        )

    fake.generate_payment_book = book


@pytest.mark.django_db
def test_generate_charges_accepts_book_error_when_charges_were_created():
    tenant, sub = _qa_tenant()
    fake = FakeSandbox(sub, [])
    _book_refused(fake, creates=True)
    target = timezone.localdate().replace(day=1) + timedelta(days=40)

    with mock.patch(CLIENT_PATH, return_value=fake):
        output = _run(
            "generate-charges",
            tenant_id=tenant.pk,
            confirm_slug=tenant.slug,
            until=f"{target.year}-{target.month:02d}",
        )

    assert "[OK   ] [SANDBOX] Cobranças futuras geradas na assinatura" in output
    assert "mas as cobranças foram criadas" in output


@pytest.mark.django_db
def test_generate_charges_fails_when_book_error_created_nothing():
    tenant, sub = _qa_tenant()
    fake = FakeSandbox(sub, [])
    _book_refused(fake, creates=False)
    target = timezone.localdate().replace(day=1) + timedelta(days=40)

    with mock.patch(CLIENT_PATH, return_value=fake), pytest.raises(CommandError, match="paymentBook recusado"):
        _run(
            "generate-charges",
            tenant_id=tenant.pk,
            confirm_slug=tenant.slug,
            until=f"{target.year}-{target.month:02d}",
        )


@pytest.mark.django_db
def test_generate_charges_limits_the_period():
    tenant, sub = _qa_tenant()
    fake = FakeSandbox(sub, [])
    far = timezone.localdate() + timedelta(days=400)

    with mock.patch(CLIENT_PATH, return_value=fake), pytest.raises(CommandError, match="meses"):
        _run(
            "generate-charges",
            tenant_id=tenant.pk,
            confirm_slug=tenant.slug,
            until=f"{far.year}-{far.month:02d}",
        )
    assert fake.calls == []


# --------------------------------------------------------------------------- carência


@pytest.mark.django_db
def test_advance_grace_requires_overdue_from_real_charge():
    tenant, _ = _qa_tenant(subscription_status=Tenant.SubscriptionStatus.OVERDUE, overdue_since=timezone.now())

    with pytest.raises(CommandError, match="cobrança exigida"):
        _run("advance-grace", tenant_id=tenant.pk, confirm_slug=tenant.slug)

    assert not QaBillingSnapshot.objects.exists()


@pytest.mark.django_db
def test_advance_grace_refuses_extending_the_grace():
    tenant, sub = _qa_tenant()
    _overdue_via_sandbox(tenant, sub, "pay_a")

    with pytest.raises(CommandError, match="não é uma antecipação"):
        _run("advance-grace", tenant_id=tenant.pk, confirm_slug=tenant.slug, ends_in_minutes=10 * 24 * 60)


@pytest.mark.django_db
def test_advance_grace_dry_run_changes_nothing():
    tenant, sub = _qa_tenant()
    _overdue_via_sandbox(tenant, sub, "pay_a")
    tenant.refresh_from_db()
    before = tenant.overdue_since

    output = _run("advance-grace", tenant_id=tenant.pk, confirm_slug=tenant.slug, dry_run=True)

    tenant.refresh_from_db()
    assert "[dry-run] nada foi alterado." in output
    assert tenant.overdue_since == before
    assert not QaBillingSnapshot.objects.exists()


@pytest.mark.django_db
def test_advance_grace_only_shifts_selected_tenant_and_keeps_status(settings):
    tenant, sub = _qa_tenant()
    other, other_sub = _qa_tenant()
    _overdue_via_sandbox(tenant, sub, "pay_a")
    _overdue_via_sandbox(other, other_sub, "pay_b")
    tenant.refresh_from_db()
    other.refresh_from_db()
    original_since = tenant.overdue_since
    original_charge_at = SubscriptionCharge.objects.get(asaas_payment_id="pay_a").overdue_at
    other_since = other.overdue_since

    _run("advance-grace", tenant_id=tenant.pk, confirm_slug=tenant.slug, ends_in_minutes=5)

    tenant.refresh_from_db()
    other.refresh_from_db()
    shift = tenant.overdue_since - original_since
    assert tenant.subscription_status == Tenant.SubscriptionStatus.OVERDUE
    assert tenant.is_in_grace_period()
    assert abs((grace_deadline(tenant.overdue_since) - timezone.now()) - timedelta(minutes=5)) < timedelta(seconds=30)
    assert SubscriptionCharge.objects.get(asaas_payment_id="pay_a").overdue_at == original_charge_at + shift
    assert other.overdue_since == other_since
    assert settings.BILLING_GRACE_DAYS == 3
    snapshot = QaBillingSnapshot.objects.get(tenant=tenant)
    assert snapshot.data["tenant"]["overdue_since"] == original_since.isoformat()


# --------------------------------------------------------------------------- ciclo completo


@pytest.mark.django_db
def test_full_cycle_grace_block_partial_payment_and_release(summary_client, no_external_calls):
    tenant, sub = _qa_tenant()
    control, _ = _qa_tenant()
    WhatsappInstanceFactory(tenant=tenant)
    fake = _overdue_via_sandbox(tenant, sub, "pay_a", "pay_b")

    with mock.patch(CLIENT_PATH, return_value=fake):
        grace = _run("validate", tenant_id=tenant.pk, expect="grace", control_tenant_id=control.pk)
    assert "FALHA" not in grace

    _run("advance-grace", tenant_id=tenant.pk, confirm_slug=tenant.slug)
    check_out = _run("run-check", tenant_id=tenant.pk, confirm_slug=tenant.slug, simulate_logout_failure=True)
    tenant.refresh_from_db()
    assert "1 suspenso(s)" in check_out
    assert tenant.subscription_status == Tenant.SubscriptionStatus.SUSPENDED
    assert tenant.whatsapp_logout_pending_since is not None
    assert tenant.whatsapp_logout_attempts == 1
    assert "QA: falha simulada" in tenant.whatsapp_logout_last_error

    blocked = _run("validate", tenant_id=tenant.pk, expect="blocked", control_tenant_id=control.pk)
    assert "FALHA" not in blocked
    assert "API protegida retorna 402" in blocked
    assert "Resumo de cobrança acessível (GET /api/settings/billing/payment-method/): HTTP 200 faturas_exigidas=2" in blocked
    assert "Controle: painel liberado" in blocked
    assert not ChatSession.objects.filter(tenant=tenant).exists()

    with mock.patch(CLIENT_PATH, return_value=fake):
        _run("confirm-payment", tenant_id=tenant.pk, confirm_slug=tenant.slug, payment_id="pay_a", wait=1)
    tenant.refresh_from_db()
    assert tenant.subscription_status == Tenant.SubscriptionStatus.SUSPENDED

    with mock.patch(CLIENT_PATH, return_value=fake):
        duplicate = _run("replay-webhook", tenant_id=tenant.pk, mode="duplicate", payment_id="pay_a")
        stale = _run("replay-webhook", tenant_id=tenant.pk, mode="stale", payment_id="pay_a")
    assert "[OK   ] [SIMULADO] Estado do tenant e do ledger inalterado" in duplicate
    assert "[OK   ] [SIMULADO] Estado do tenant e do ledger inalterado" in stale
    tenant.refresh_from_db()
    assert tenant.subscription_status == Tenant.SubscriptionStatus.SUSPENDED

    with mock.patch(CLIENT_PATH, return_value=fake):
        _run("confirm-payment", tenant_id=tenant.pk, confirm_slug=tenant.slug, payment_id="pay_b", wait=1)
    active = _run("validate", tenant_id=tenant.pk, expect="active", control_tenant_id=control.pk)
    assert "FALHA" not in active
    tenant.refresh_from_db()
    assert tenant.subscription_status == Tenant.SubscriptionStatus.ACTIVE
    assert no_external_calls.call_count == 2


@pytest.mark.django_db
def test_validate_blocked_fails_while_still_in_grace(summary_client):
    tenant, sub = _qa_tenant()
    _overdue_via_sandbox(tenant, sub, "pay_a")

    with pytest.raises(CommandError, match="falharam"):
        _run("validate", tenant_id=tenant.pk, expect="blocked")

    tenant.refresh_from_db()
    assert tenant.subscription_status == Tenant.SubscriptionStatus.OVERDUE


@pytest.mark.django_db
def test_bot_probe_stops_at_access_check_without_side_effects():
    tenant, _ = _qa_tenant()
    WhatsappInstanceFactory(tenant=tenant)

    with mock.patch("apps.integrations.services.webhook_handlers.send_whatsapp_reply") as send:
        assert qa.probe_bot_gate(tenant) is True

    send.assert_not_called()
    assert not ChatSession.objects.filter(tenant=tenant).exists()


@pytest.mark.django_db
def test_bot_probe_denied_for_suspended_tenant_even_with_logout_pending():
    tenant, _ = _qa_tenant(
        subscription_status=Tenant.SubscriptionStatus.SUSPENDED,
        billing_blocked_at=timezone.now(),
        whatsapp_logout_pending_since=timezone.now(),
    )
    WhatsappInstanceFactory(tenant=tenant)

    assert qa.probe_bot_gate(tenant) is False


# --------------------------------------------------------------------------- restauração


@pytest.mark.django_db
def test_restore_returns_scenario_to_values_before_advance():
    tenant, sub = _qa_tenant()
    _overdue_via_sandbox(tenant, sub, "pay_a")
    tenant.refresh_from_db()
    original_since = tenant.overdue_since
    _run("advance-grace", tenant_id=tenant.pk, confirm_slug=tenant.slug)
    with mock.patch(LOGOUT_SESSION_PATH):
        _run("run-check", tenant_id=tenant.pk, confirm_slug=tenant.slug)
    tenant.refresh_from_db()
    assert tenant.subscription_status == Tenant.SubscriptionStatus.SUSPENDED

    preview = _run("restore", tenant_id=tenant.pk, confirm_slug=tenant.slug, dry_run=True)
    tenant.refresh_from_db()
    assert "tenant.subscription_status: SUSPENDED → OVERDUE" in preview
    assert tenant.subscription_status == Tenant.SubscriptionStatus.SUSPENDED

    _run("restore", tenant_id=tenant.pk, confirm_slug=tenant.slug)

    tenant.refresh_from_db()
    assert tenant.subscription_status == Tenant.SubscriptionStatus.OVERDUE
    assert tenant.overdue_since == original_since
    assert tenant.billing_blocked_at is None
    assert tenant.is_in_grace_period()
    assert QaBillingSnapshot.objects.get(tenant=tenant).restored_at is not None


@pytest.mark.django_db
def test_restore_refused_after_required_charge_was_paid():
    tenant, sub = _qa_tenant()
    fake = _overdue_via_sandbox(tenant, sub, "pay_a")
    _run("advance-grace", tenant_id=tenant.pk, confirm_slug=tenant.slug)
    with mock.patch(CLIENT_PATH, return_value=fake):
        _run("confirm-payment", tenant_id=tenant.pk, confirm_slug=tenant.slug, payment_id="pay_a", wait=1)

    with pytest.raises(CommandError, match="quitadas"):
        _run("restore", tenant_id=tenant.pk, confirm_slug=tenant.slug)

    tenant.refresh_from_db()
    assert tenant.subscription_status == Tenant.SubscriptionStatus.ACTIVE

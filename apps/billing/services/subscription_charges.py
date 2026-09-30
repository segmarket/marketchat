"""
Ledger das cobranças da assinatura SaaS e regra única de regularização.

Uma cobrança (pay_…) vira "exigida" quando vence ou o cartão é recusado; o tenant só
volta a ter acesso quando essa cobrança específica é confirmada como paga e não resta
nenhuma outra exigida. Eventos antigos, duplicados ou fora de ordem não mudam o estado.
"""

from __future__ import annotations

import logging
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from django.utils import timezone
from django.utils.dateparse import parse_date, parse_datetime

from apps.billing.models import Subscription, SubscriptionCharge
from apps.billing.services.asaas_client import AsaasAPIError, AsaasClient
from apps.tenants.models import Tenant

logger = logging.getLogger(__name__)

PAID_STATUSES = frozenset({"CONFIRMED", "RECEIVED", "RECEIVED_IN_CASH"})
PAYABLE_STATUSES = frozenset({"PENDING", "OVERDUE"})


def parse_asaas_date(value: Any) -> date | None:
    if not value or not isinstance(value, str):
        return None
    return parse_date(value.strip()[:10])


def parse_asaas_datetime(value: Any) -> datetime | None:
    """Asaas envia `dateCreated` como "YYYY-MM-DD HH:MM:SS" no fuso da conta (America/Sao_Paulo)."""
    if not value or not isinstance(value, str):
        return None
    parsed = parse_datetime(value.strip())
    if parsed is None:
        return None
    if timezone.is_naive(parsed):
        parsed = timezone.make_aware(parsed, timezone.get_default_timezone())
    return parsed


def payment_id_of(payment: dict[str, Any]) -> str:
    pid = payment.get("id")
    return str(pid).strip() if isinstance(pid, str) else ""


def payment_status_of(payment: dict[str, Any]) -> str:
    return str(payment.get("status") or "").strip().upper()


def payment_subscription_id_of(payment: dict[str, Any]) -> str:
    sid = payment.get("subscription")
    if isinstance(sid, dict):
        sid = sid.get("id")
    return str(sid).strip() if isinstance(sid, str) else ""


def _decimal_or_none(value: Any) -> Decimal | None:
    if value is None:
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


def upsert_charge(
    sub: Subscription,
    payment: dict[str, Any],
    *,
    event: str = "",
    event_at: datetime | None = None,
) -> SubscriptionCharge | None:
    payment_id = payment_id_of(payment)
    if not payment_id:
        return None

    charge, _ = SubscriptionCharge.objects.select_for_update().get_or_create(
        asaas_payment_id=payment_id,
        defaults={
            "subscription": sub,
            "asaas_subscription_id": payment_subscription_id_of(payment) or sub.asaas_subscription_id,
        },
    )
    due = parse_asaas_date(payment.get("dueDate"))
    if due:
        charge.due_date = due
    original_due = parse_asaas_date(payment.get("originalDueDate"))
    if original_due:
        charge.original_due_date = original_due
    value = _decimal_or_none(payment.get("value"))
    if value is not None:
        charge.value = value
    status = payment_status_of(payment)
    if status:
        charge.asaas_status = status
    if event:
        charge.last_event = event
        charge.last_event_at = event_at or timezone.now()
    charge.save()
    return charge


def mark_charge_paid(charge: SubscriptionCharge, *, when: datetime | None = None) -> bool:
    """Retorna True apenas na primeira confirmação (idempotente)."""
    if charge.paid_at is not None:
        return False
    charge.paid_at = when or timezone.now()
    charge.save(update_fields=["paid_at", "updated_at"])
    return True


def mark_charge_required(charge: SubscriptionCharge, *, when: datetime | None = None) -> bool:
    if charge.paid_at is not None or charge.removed_at is not None:
        return False
    if charge.overdue_at is not None:
        return False
    charge.overdue_at = when or timezone.now()
    charge.save(update_fields=["overdue_at", "updated_at"])
    return True


def mark_charge_removed(charge: SubscriptionCharge, *, when: datetime | None = None) -> bool:
    if charge.paid_at is not None or charge.removed_at is not None:
        return False
    charge.removed_at = when or timezone.now()
    charge.save(update_fields=["removed_at", "updated_at"])
    return True


def outstanding_charges(sub: Subscription):
    return SubscriptionCharge.objects.filter(
        subscription=sub,
        asaas_subscription_id=sub.asaas_subscription_id,
        overdue_at__isnull=False,
        paid_at__isnull=True,
        removed_at__isnull=True,
    ).order_by("original_due_date", "due_date", "pk")


def sync_overdue_charges_from_asaas(
    sub: Subscription,
    *,
    client: AsaasClient | None = None,
    include_pending_due: bool = False,
) -> list[SubscriptionCharge] | None:
    """
    Consulta no Asaas as cobranças OVERDUE da assinatura atual e as registra como exigidas.
    Com include_pending_due, inclui PENDING já vencendo (ex.: 1ª cobrança ao fim do trial).
    Retorna None se a consulta falhar (não há prova de quitação).
    """
    client = client or AsaasClient()
    statuses = ["OVERDUE", "PENDING"] if include_pending_due else ["OVERDUE"]
    today = timezone.localdate()
    found: list[SubscriptionCharge] = []
    for status in statuses:
        try:
            data = client.list_payments(
                subscription=sub.asaas_subscription_id,
                status=status,
                limit=100,
            )
        except AsaasAPIError as exc:
            logger.warning(
                "Asaas: falha ao listar cobranças status=%s subscription=%s err=%s",
                status,
                sub.asaas_subscription_id,
                exc,
            )
            return None

        for item in (data or {}).get("data") or []:
            if not isinstance(item, dict):
                continue
            if payment_subscription_id_of(item) not in ("", sub.asaas_subscription_id):
                continue
            item_status = payment_status_of(item)
            if item_status in PAID_STATUSES:
                continue
            if item_status == "PENDING":
                due = parse_asaas_date(item.get("dueDate"))
                if due is None or due > today:
                    continue
            charge = upsert_charge(sub, item, event=f"SYNC_{status}")
            if charge is None or charge.paid_at is not None or charge.removed_at is not None:
                continue
            mark_charge_required(charge)
            if charge not in found:
                found.append(charge)
    return found


def mark_tenant_overdue(tenant: Tenant, sub: Subscription) -> None:
    if tenant.subscription_status == Tenant.SubscriptionStatus.CANCELED:
        return

    if sub.status != Subscription.Status.OVERDUE:
        sub.status = Subscription.Status.OVERDUE
        sub.save(update_fields=["status", "updated_at"])

    if tenant.subscription_status == Tenant.SubscriptionStatus.SUSPENDED:
        return

    tenant.subscription_status = Tenant.SubscriptionStatus.OVERDUE
    update_fields = ["subscription_status", "updated_at"]
    if tenant.overdue_since is None:
        tenant.overdue_since = timezone.now()
        update_fields.append("overdue_since")
    tenant.save(update_fields=update_fields)


def activate_tenant(tenant: Tenant, sub: Subscription, *, reason: str) -> None:
    previous = tenant.subscription_status
    tenant.subscription_status = Tenant.SubscriptionStatus.ACTIVE
    tenant.overdue_since = None
    tenant.billing_blocked_at = None
    tenant.whatsapp_logout_pending_since = None
    tenant.save(
        update_fields=[
            "subscription_status",
            "overdue_since",
            "billing_blocked_at",
            "whatsapp_logout_pending_since",
            "updated_at",
        ],
    )
    if sub.status != Subscription.Status.ACTIVE:
        sub.status = Subscription.Status.ACTIVE
        sub.save(update_fields=["status", "updated_at"])
    if previous != Tenant.SubscriptionStatus.ACTIVE:
        logger.info(
            "Tenant regularizado tenant_id=%s de=%s motivo=%s",
            tenant.pk,
            previous,
            reason,
        )


def settle_after_payment(
    tenant: Tenant,
    sub: Subscription,
    charge: SubscriptionCharge,
    *,
    newly_paid: bool,
    was_required: bool,
    client: AsaasClient | None = None,
) -> str:
    """
    Decide se o pagamento confirmado de `charge` libera o acesso. Retorna o desfecho.

    - CANCELED nunca é reativado por evento de pagamento (só pelo fluxo de reativação).
    - OVERDUE/SUSPENDED só voltam se a cobrança paga era a exigida e nenhuma outra resta;
      sem exigida rastreada (estado anterior ao ledger), o Asaas precisa confirmar que a
      assinatura não tem cobrança vencida.
    """
    status = tenant.subscription_status
    if status == Tenant.SubscriptionStatus.CANCELED:
        return "ignored_canceled"
    if not newly_paid:
        return "already_paid"
    if charge.asaas_subscription_id != sub.asaas_subscription_id:
        return "ignored_other_subscription"
    if outstanding_charges(sub).exists():
        return "outstanding_remaining"

    if status in (Tenant.SubscriptionStatus.TRIAL, Tenant.SubscriptionStatus.ACTIVE):
        activate_tenant(tenant, sub, reason="payment_confirmed")
        return "activated"

    if was_required:
        activate_tenant(tenant, sub, reason="required_charge_paid")
        return "regularized"

    remaining = sync_overdue_charges_from_asaas(sub, client=client)
    if remaining is None:
        logger.warning(
            "Pagamento sem vínculo comprovado (Asaas indisponível) tenant_id=%s payment=%s",
            tenant.pk,
            charge.asaas_payment_id,
        )
        return "unproven_link"
    if remaining:
        logger.info(
            "Pagamento não quita a pendência tenant_id=%s payment=%s exigidas=%s",
            tenant.pk,
            charge.asaas_payment_id,
            [c.asaas_payment_id for c in remaining],
        )
        return "outstanding_remaining"
    activate_tenant(tenant, sub, reason="asaas_confirms_no_overdue")
    return "regularized_remote_check"


def register_charge_failure(
    tenant: Tenant,
    sub: Subscription,
    charge: SubscriptionCharge | None,
    *,
    payment_status: str,
    when: datetime | None = None,
) -> str:
    if payment_status in PAID_STATUSES:
        return "ignored_paid_status"
    if charge is not None:
        if charge.paid_at is not None:
            return "ignored_already_paid"
        if charge.removed_at is not None:
            return "ignored_removed"
        if charge.asaas_subscription_id != sub.asaas_subscription_id:
            return "ignored_other_subscription"
        mark_charge_required(charge, when=when)
    if tenant.subscription_status == Tenant.SubscriptionStatus.CANCELED:
        return "ignored_canceled"
    mark_tenant_overdue(tenant, sub)
    return "marked_overdue"

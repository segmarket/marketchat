from __future__ import annotations

import logging
from typing import Any

from django.utils import timezone

from apps.accounts.models import User
from apps.billing.models import Subscription
from apps.billing.services.asaas_webhook_payload import normalize_asaas_webhook
from apps.billing.services.meta_capi import schedule_meta_purchase_event
from apps.financial.services.asaas_transfer_webhook import process_transfer_asaas_event
from apps.sales.services.asaas_payment_webhook import process_cart_asaas_event
from apps.tenants.models import Tenant

logger = logging.getLogger(__name__)

PAYMENT_SUCCESS_EVENTS = frozenset({"PAYMENT_CONFIRMED", "PAYMENT_RECEIVED"})

PAYMENT_FAILURE_EVENTS = frozenset(
    {
        "PAYMENT_OVERDUE",
        "PAYMENT_REJECTED",
        "PAYMENT_REFUSED",
        "PAYMENT_FAILED",
    },
)

SUBSCRIPTION_CANCELLATION_EVENTS = frozenset(
    {
        "SUBSCRIPTION_DELETED",
        "SUBSCRIPTION_CANCELED",
    },
)


def _subscription_id_from_payment(payment: dict[str, Any]) -> str | None:
    sid = payment.get("subscription")
    if isinstance(sid, str):
        return sid
    if isinstance(sid, dict):
        return sid.get("id")
    return None


def _activate_tenant_subscription(tenant: Tenant, sub: Subscription) -> None:
    tenant.clear_billing_block()
    tenant.subscription_status = Tenant.SubscriptionStatus.ACTIVE
    tenant.overdue_since = None
    tenant.save(
        update_fields=[
            "subscription_status",
            "overdue_since",
            "billing_blocked_at",
            "updated_at",
        ],
    )
    if sub.status != Subscription.Status.ACTIVE:
        sub.status = Subscription.Status.ACTIVE
        sub.save(update_fields=["status", "updated_at"])


def _mark_tenant_overdue(tenant: Tenant, sub: Subscription) -> None:
    if tenant.subscription_status == Tenant.SubscriptionStatus.CANCELED:
        return

    sub.status = Subscription.Status.OVERDUE
    sub.save(update_fields=["status", "updated_at"])

    tenant.subscription_status = Tenant.SubscriptionStatus.OVERDUE
    update_fields = ["subscription_status", "updated_at"]
    if tenant.overdue_since is None:
        tenant.overdue_since = timezone.now()
        update_fields.append("overdue_since")
    tenant.save(update_fields=update_fields)


def _schedule_purchase_for_tenant(tenant: Tenant, payment: dict[str, Any]) -> None:
    """Dispara Purchase (Meta CAPI) em background após pagamento de assinatura confirmado."""
    admin = (
        User.objects.filter(tenant=tenant, is_tenant_admin=True)
        .order_by("id")
        .first()
    )
    email = (admin.email if admin else "") or ""
    phone = ""
    if admin and (admin.phone or "").strip():
        phone = admin.phone.strip()
    elif (tenant.phone or "").strip():
        phone = tenant.phone.strip()

    raw_value = payment.get("value")
    try:
        value = float(raw_value) if raw_value is not None else 0.0
    except (TypeError, ValueError):
        value = 0.0
    if value <= 0:
        value = tenant.computed_subscription_value()

    payment_id = payment.get("id")
    event_id = str(payment_id) if payment_id else None

    schedule_meta_purchase_event(
        email,
        phone,
        value,
        currency="BRL",
        event_id=event_id,
    )


def _handle_subscription_cancellation_event(tenant: Tenant, sub: Subscription) -> None:
    """
    Cancelamento definitivo só se o tenant já foi cancelado manualmente.
    Caso contrário (ex.: assinatura removida pelo gateway após falha de cobrança),
    entra em OVERDUE para a régua de carência.
    """
    if tenant.subscription_status == Tenant.SubscriptionStatus.CANCELED:
        from apps.billing.services.subscription_cancel import _apply_local_cancellation

        _apply_local_cancellation(tenant, sub)
        return

    _mark_tenant_overdue(tenant, sub)


def _process_subscription_webhook(*, event: str, payment: dict[str, Any], payload: dict[str, Any]) -> None:
    subscription_block = payload.get("subscription")
    sub_id: str | None = None
    if isinstance(subscription_block, dict):
        sid = subscription_block.get("id")
        if sid:
            sub_id = str(sid)
    if not sub_id:
        sub_id = _subscription_id_from_payment(payment)
        if sub_id:
            sub_id = str(sub_id)

    if not sub_id:
        logger.info("Webhook Asaas sem subscription id: event=%s", event)
        return

    sub = Subscription.objects.filter(asaas_subscription_id=sub_id).select_related("tenant").first()
    if not sub:
        logger.info("Subscription local não encontrada para Asaas id=%s", sub_id)
        return

    tenant = sub.tenant

    if event in PAYMENT_SUCCESS_EVENTS:
        _activate_tenant_subscription(tenant, sub)
        _schedule_purchase_for_tenant(tenant, payment)
        return

    if event in PAYMENT_FAILURE_EVENTS:
        _mark_tenant_overdue(tenant, sub)
        return

    if event in SUBSCRIPTION_CANCELLATION_EVENTS:
        _handle_subscription_cancellation_event(tenant, sub)
        return

    logger.debug("Evento Asaas (assinatura) não tratado: %s", event)


def process_asaas_webhook_payload(payload: dict[str, Any]) -> None:
    """
    Processa webhooks do Asaas: carrinhos WhatsApp (Pix) e assinaturas SaaS.
    Estrutura típica: {"event": "PAYMENT_RECEIVED", "payment": {...}}.
    """
    event, payment = normalize_asaas_webhook(payload)
    transfer = payload.get("transfer") if isinstance(payload.get("transfer"), dict) else {}

    logger.info(
        "Webhook Asaas recebido: event=%s payment_id=%s transfer_id=%s externalReference=%s",
        event,
        payment.get("id"),
        transfer.get("id"),
        payment.get("externalReference") or transfer.get("externalReference"),
    )

    if process_transfer_asaas_event(event=event, payload=payload):
        return

    if process_cart_asaas_event(event=event, payment=payment):
        return

    _process_subscription_webhook(event=event, payment=payment, payload=payload)

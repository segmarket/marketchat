from __future__ import annotations

import hashlib
import json
import logging
from typing import Any

from django.db import transaction
from django.utils import timezone

from apps.accounts.models import User
from apps.billing.models import AsaasWebhookEvent, Subscription, SubscriptionCharge
from apps.billing.services.asaas_webhook_payload import normalize_asaas_webhook
from apps.billing.services.meta_capi import schedule_meta_purchase_event
from apps.billing.services.subscription_charges import (
    PAID_STATUSES,
    mark_charge_paid,
    mark_charge_removed,
    mark_tenant_overdue,
    parse_asaas_datetime,
    payment_id_of,
    payment_status_of,
    payment_subscription_id_of,
    register_charge_failure,
    settle_after_payment,
    upsert_charge,
)
from apps.financial.services.asaas_transfer_webhook import process_transfer_asaas_event
from apps.sales.services.asaas_payment_webhook import process_cart_asaas_event
from apps.tenants.models import Tenant

logger = logging.getLogger(__name__)

PAYMENT_SUCCESS_EVENTS = frozenset({"PAYMENT_CONFIRMED", "PAYMENT_RECEIVED"})

# PAYMENT_OVERDUE e PAYMENT_CREDIT_CARD_CAPTURE_REFUSED são os eventos documentados pelo
# Asaas; os demais nomes são mantidos por compatibilidade com integrações antigas.
PAYMENT_FAILURE_EVENTS = frozenset(
    {
        "PAYMENT_OVERDUE",
        "PAYMENT_CREDIT_CARD_CAPTURE_REFUSED",
        "PAYMENT_REJECTED",
        "PAYMENT_REFUSED",
        "PAYMENT_FAILED",
    },
)

PAYMENT_REMOVED_EVENTS = frozenset({"PAYMENT_DELETED"})

SUBSCRIPTION_CANCELLATION_EVENTS = frozenset(
    {
        "SUBSCRIPTION_DELETED",
        "SUBSCRIPTION_CANCELED",
    },
)


def _event_key(payload: dict[str, Any]) -> str:
    """`id` do evento (evt_…) quando presente; senão, impressão digital do corpo."""
    root_id = str(payload.get("id") or "").strip()
    if root_id and not root_id.startswith("pay_"):
        return root_id[:191]
    canonical = json.dumps(payload, sort_keys=True, default=str, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()


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


def _handle_subscription_cancellation_event(tenant: Tenant, sub: Subscription) -> str:
    """
    Cancelamento definitivo só se o tenant já foi cancelado manualmente.
    Caso contrário (ex.: assinatura removida pelo gateway após falha de cobrança),
    entra em OVERDUE para a régua de carência.
    """
    if tenant.subscription_status == Tenant.SubscriptionStatus.CANCELED:
        from apps.billing.services.subscription_cancel import _apply_local_cancellation

        _apply_local_cancellation(tenant, sub)
        return "canceled"

    mark_tenant_overdue(tenant, sub)
    return "marked_overdue"


def _resolve_subscription(payment: dict[str, Any], payload: dict[str, Any]) -> Subscription | None:
    payment_id = payment_id_of(payment)
    if payment_id:
        charge = (
            SubscriptionCharge.objects.filter(asaas_payment_id=payment_id)
            .select_related("subscription")
            .first()
        )
        if charge is not None:
            return charge.subscription

    sub_id = ""
    subscription_block = payload.get("subscription")
    if isinstance(subscription_block, dict) and subscription_block.get("id"):
        sub_id = str(subscription_block["id"]).strip()
    if not sub_id:
        sub_id = payment_subscription_id_of(payment)
    if not sub_id:
        return None
    return Subscription.objects.filter(asaas_subscription_id=sub_id).first()


def _apply_subscription_event(
    *,
    event: str,
    payment: dict[str, Any],
    tenant: Tenant,
    sub: Subscription,
    event_at,
) -> tuple[str, bool]:
    """Aplica o evento ao ledger e ao tenant. Retorna (desfecho, cobrança recém-paga)."""
    if event in SUBSCRIPTION_CANCELLATION_EVENTS:
        return _handle_subscription_cancellation_event(tenant, sub), False

    charge = upsert_charge(sub, payment, event=event, event_at=event_at)
    status = payment_status_of(payment)

    if event in PAYMENT_SUCCESS_EVENTS:
        if charge is None:
            return "ignored_without_payment_id", False
        if status and status not in PAID_STATUSES:
            return "ignored_status_not_paid", False
        was_required = charge.is_outstanding
        newly_paid = mark_charge_paid(charge, when=event_at)
        outcome = settle_after_payment(
            tenant,
            sub,
            charge,
            newly_paid=newly_paid,
            was_required=was_required,
        )
        return outcome, newly_paid

    if event in PAYMENT_FAILURE_EVENTS:
        outcome = register_charge_failure(
            tenant,
            sub,
            charge,
            payment_status=status,
            when=event_at,
        )
        return outcome, False

    if event in PAYMENT_REMOVED_EVENTS and charge is not None:
        return ("charge_removed" if mark_charge_removed(charge, when=event_at) else "noop"), False

    return ("recorded" if charge is not None else "ignored"), False


def _process_subscription_webhook(*, event: str, payment: dict[str, Any], payload: dict[str, Any]) -> None:
    found = _resolve_subscription(payment, payload)
    if found is None:
        logger.info(
            "Webhook Asaas sem assinatura local: event=%s payment_id=%s",
            event,
            payment_id_of(payment),
        )
        return

    event_key = _event_key(payload)
    event_at = parse_asaas_datetime(payload.get("dateCreated")) or timezone.now()
    newly_paid = False

    with transaction.atomic():
        tenant = Tenant.objects.select_for_update().get(pk=found.tenant_id)
        sub = Subscription.objects.select_for_update().get(pk=found.pk)
        record, created = AsaasWebhookEvent.objects.get_or_create(
            event_key=event_key,
            defaults={
                "event": event[:64],
                "asaas_payment_id": payment_id_of(payment)[:64],
                "asaas_subscription_id": sub.asaas_subscription_id,
                "event_created_at": parse_asaas_datetime(payload.get("dateCreated")),
            },
        )
        if not created and record.processed_at is not None:
            logger.info(
                "Webhook Asaas duplicado ignorado: key=%s event=%s outcome=%s",
                event_key,
                event,
                record.outcome,
            )
            return

        outcome, newly_paid = _apply_subscription_event(
            event=event,
            payment=payment,
            tenant=tenant,
            sub=sub,
            event_at=event_at,
        )
        record.outcome = outcome[:64]
        record.processed_at = timezone.now()
        record.save(update_fields=["outcome", "processed_at"])

    logger.info(
        "Webhook Asaas (assinatura): event=%s payment_id=%s tenant=%s outcome=%s",
        event,
        payment_id_of(payment),
        tenant.pk,
        outcome,
    )
    if newly_paid:
        _schedule_purchase_for_tenant(tenant, payment)


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

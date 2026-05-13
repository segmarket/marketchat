from __future__ import annotations

import logging
from typing import Any

from apps.billing.models import Subscription

logger = logging.getLogger(__name__)


def _subscription_id_from_payment(payment: dict[str, Any]) -> str | None:
    sid = payment.get("subscription")
    if isinstance(sid, str):
        return sid
    if isinstance(sid, dict):
        return sid.get("id")
    return None


def process_asaas_webhook_payload(payload: dict[str, Any]) -> None:
    """
    Processa eventos principais do webhook Asaas.
    Estrutura típica: {"event": "PAYMENT_CONFIRMED", "payment": {...}}.
    """
    event = (payload.get("event") or payload.get("type") or "").upper()
    payment = payload.get("payment")
    if not isinstance(payment, dict):
        payment = {}

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

    if event == "PAYMENT_CONFIRMED":
        sub.tenant.clear_billing_block()
        if sub.status != Subscription.Status.ACTIVE:
            sub.status = Subscription.Status.ACTIVE
            sub.save(update_fields=["status", "updated_at"])
        return

    if event == "PAYMENT_OVERDUE":
        sub.status = Subscription.Status.OVERDUE
        sub.save(update_fields=["status", "updated_at"])
        sub.tenant.block_billing_access()
        return

    if event == "SUBSCRIPTION_DELETED":
        sub.status = Subscription.Status.CANCELLED
        sub.save(update_fields=["status", "updated_at"])
        sub.tenant.block_billing_access()
        return

    logger.debug("Evento Asaas não tratado: %s", event)

from __future__ import annotations

import logging
from typing import Any

from apps.financial.models import WithdrawalRequest
from apps.financial.services.asaas_transfers import ASAAS_PAID_TRANSFER_STATUSES
from apps.financial.services.wallet import mark_withdrawal_paid, mark_withdrawal_rejected

logger = logging.getLogger(__name__)

WITHDRAW_EXTERNAL_REF_PREFIX = "marketchat-withdraw-"

TRANSFER_SUCCESS_EVENTS = frozenset({"TRANSFER_DONE"})

TRANSFER_FAILURE_EVENTS = frozenset(
    {
        "TRANSFER_FAILED",
        "TRANSFER_CANCELLED",
        "TRANSFER_REFUSED",
    },
)

ASAAS_FAILED_TRANSFER_STATUSES = frozenset(
    {
        "FAILED",
        "CANCELLED",
        "REFUSED",
        "REJECTED",
    },
)


def _extract_transfer(payload: dict[str, Any]) -> dict[str, Any] | None:
    transfer = payload.get("transfer")
    if isinstance(transfer, dict) and transfer.get("id"):
        return transfer
    return None


def _is_marketchat_withdraw(transfer: dict[str, Any]) -> bool:
    ref = str(transfer.get("externalReference") or "").strip()
    if ref.startswith(WITHDRAW_EXTERNAL_REF_PREFIX):
        return True
    return str(transfer.get("description") or "").strip() == "Saque MarketChat"


def _find_withdrawal(transfer: dict[str, Any]) -> WithdrawalRequest | None:
    transfer_id = str(transfer.get("id") or "").strip()
    if not transfer_id:
        return None
    return WithdrawalRequest.objects.filter(asaas_transfer_id=transfer_id).first()


def process_transfer_asaas_event(*, event: str, payload: dict[str, Any]) -> bool:
    """
    Atualiza WithdrawalRequest a partir de webhooks de transferência Pix do Asaas.
    Retorna True quando o payload é um evento de transferência MarketChat.
    """
    transfer = _extract_transfer(payload)
    if transfer is None:
        return False

    if not _is_marketchat_withdraw(transfer):
        return False

    event_name = str(event or "").strip().upper()
    transfer_id = str(transfer.get("id") or "").strip()
    transfer_status = str(transfer.get("status") or "").strip().upper()

    withdrawal = _find_withdrawal(transfer)
    if withdrawal is None:
        logger.info(
            "Webhook transfer sem withdrawal local: transfer=%s event=%s ref=%s",
            transfer_id,
            event_name,
            transfer.get("externalReference"),
        )
        return True

    if event_name in TRANSFER_SUCCESS_EVENTS or transfer_status in ASAAS_PAID_TRANSFER_STATUSES:
        if mark_withdrawal_paid(withdrawal):
            logger.info(
                "Saque confirmado via webhook: withdrawal=%s transfer=%s event=%s",
                withdrawal.id,
                transfer_id,
                event_name,
            )
        return True

    if event_name in TRANSFER_FAILURE_EVENTS or transfer_status in ASAAS_FAILED_TRANSFER_STATUSES:
        if mark_withdrawal_rejected(withdrawal):
            logger.info(
                "Saque rejeitado via webhook: withdrawal=%s transfer=%s event=%s",
                withdrawal.id,
                transfer_id,
                event_name,
            )
        return True

    if event_name == "TRANSFER_CREATED":
        logger.info(
            "Webhook transfer criado: withdrawal=%s transfer=%s status=%s",
            withdrawal.id,
            transfer_id,
            transfer_status,
        )
        return True

    logger.debug(
        "Evento transfer Asaas ignorado: withdrawal=%s transfer=%s event=%s status=%s",
        withdrawal.id,
        transfer_id,
        event_name,
        transfer_status,
    )
    return True

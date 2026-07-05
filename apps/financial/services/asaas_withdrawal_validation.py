"""Validação automática de saques Pix via webhook do Asaas (Mecanismos de segurança)."""

from __future__ import annotations

import logging
import secrets
from decimal import Decimal, InvalidOperation
from typing import Any

from django.conf import settings

from apps.billing.services.asaas_webhook_payload import extract_asaas_webhook_token
from apps.financial.models import WithdrawalRequest
from apps.financial.services.asaas_transfer_webhook import WITHDRAW_EXTERNAL_REF_PREFIX

logger = logging.getLogger(__name__)

STATUS_APPROVED = "APPROVED"
STATUS_REFUSED = "REFUSED"


def verify_asaas_withdrawal_validation_request(request) -> bool:
    """
    Valida o header asaas-access-token contra ASAAS_WITHDRAWAL_TOKEN.
    Fail-closed: token ausente no servidor ou header inválido.
    """
    expected = (getattr(settings, "ASAAS_WITHDRAWAL_TOKEN", None) or "").strip()
    if not expected:
        logger.warning(
            "Validação de saque Asaas rejeitada: ASAAS_WITHDRAWAL_TOKEN não configurado"
        )
        return False

    received = extract_asaas_webhook_token(request)
    if not received:
        logger.warning(
            "Validação de saque Asaas rejeitada: header asaas-access-token ausente"
        )
        return False

    if not secrets.compare_digest(
        received.encode("utf-8"),
        expected.encode("utf-8"),
    ):
        logger.warning("Validação de saque Asaas: token inválido")
        return False

    return True


def apply_additional_withdrawal_rules(
    withdrawal: WithdrawalRequest,
    transfer: dict[str, Any],
) -> str | None:
    """
    Retorne uma string (motivo) para recusar, ou None para aprovar.
    Ex.: checar saldo, limites diários, antifraude, etc.
    """
    return None


def _is_marketchat_withdraw_transfer(transfer: dict[str, Any]) -> bool:
    ref = str(transfer.get("externalReference") or "").strip()
    if ref.startswith(WITHDRAW_EXTERNAL_REF_PREFIX):
        return True
    return str(transfer.get("description") or "").strip() == "Saque MarketChat"


def _transfer_value(transfer: dict[str, Any]) -> Decimal | None:
    raw = transfer.get("value")
    if raw is None:
        return None
    try:
        return Decimal(str(raw)).quantize(Decimal("0.01"))
    except (InvalidOperation, TypeError, ValueError):
        return None


def _extract_transfer(payload: dict[str, Any]) -> dict[str, Any] | None:
    transfer = payload.get("transfer")
    if isinstance(transfer, dict) and transfer.get("id"):
        return transfer
    return None


def _refused(reason: str) -> dict[str, str]:
    logger.info("Validação de saque Asaas recusada: %s", reason)
    return {"status": STATUS_REFUSED, "refuseReason": reason}


def build_withdrawal_validation_response(payload: dict[str, Any]) -> dict[str, str]:
    """
    Avalia o payload de transferência enviado pelo Asaas e retorna APPROVED ou REFUSED.
    """
    transfer = _extract_transfer(payload)
    if transfer is None:
        return _refused("Payload de transferência inválido ou ausente.")

    transfer_id = str(transfer.get("id") or "").strip()
    if not transfer_id:
        return _refused("Identificador da transferência ausente.")

    transfer_amount = _transfer_value(transfer)
    if transfer_amount is None:
        return _refused("Valor da transferência inválido.")

    if not _is_marketchat_withdraw_transfer(transfer):
        return _refused("Transferência não reconhecida como saque MarketChat.")

    withdrawal = WithdrawalRequest.objects.filter(
        asaas_transfer_id=transfer_id,
    ).first()
    if withdrawal is None:
        return _refused("Solicitação de saque não encontrada no sistema.")

    withdrawal_amount = withdrawal.amount.quantize(Decimal("0.01"))
    if withdrawal_amount != transfer_amount:
        return _refused("Valor da transferência não confere com o saque registrado.")

    refuse_reason = apply_additional_withdrawal_rules(withdrawal, transfer)
    if refuse_reason:
        return _refused(refuse_reason)

    logger.info(
        "Validação de saque Asaas aprovada: transfer=%s withdrawal=%s value=%s",
        transfer_id,
        withdrawal.id,
        transfer_amount,
    )
    return {"status": STATUS_APPROVED}

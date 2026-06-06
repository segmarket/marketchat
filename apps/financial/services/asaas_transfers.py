from __future__ import annotations

import logging
import uuid
from decimal import Decimal
from typing import Any

from apps.billing.services.asaas_client import AsaasAPIError, AsaasClient
from apps.billing.services.asaas_errors import format_asaas_error
from apps.financial.choices import PixKeyType

logger = logging.getLogger(__name__)

ASAAS_PAID_TRANSFER_STATUSES = frozenset(
    {
        "DONE",
        "CONFIRMED",
        "COMPLETED",
        "TRANSFERRED",
        "BANK_PROCESSING_DONE",
    },
)
ASAAS_PROCESSING_TRANSFER_STATUSES = frozenset(
    {
        "PENDING",
        "PROCESSING",
        "SCHEDULED",
        "AWAITING_APPROVAL",
        "BANK_PROCESSING",
    },
)


class AsaasTransferError(Exception):
    pass


def _digits_only(value: str) -> str:
    return "".join(c for c in value if c.isdigit())


def map_pix_key_type_to_asaas(internal_type: str) -> str:
    mapping = {
        PixKeyType.CPF: "CPF",
        PixKeyType.CNPJ: "CNPJ",
        PixKeyType.EMAIL: "EMAIL",
        PixKeyType.PHONE: "PHONE",
        PixKeyType.RANDOM: "EVP",
    }
    return mapping.get(internal_type, internal_type)


def normalize_pix_key_for_asaas(pix_key_type: str, pix_key: str) -> str:
    cleaned = (pix_key or "").strip()
    if not cleaned:
        raise AsaasTransferError("Informe a chave Pix.")

    if pix_key_type in {PixKeyType.CPF, PixKeyType.CNPJ, PixKeyType.PHONE}:
        digits = _digits_only(cleaned)
        if not digits:
            raise AsaasTransferError("Chave Pix inválida.")
        return digits

    if pix_key_type == PixKeyType.EMAIL:
        return cleaned.lower()

    return cleaned


def mask_pix_key_for_log(pix_key_type: str, pix_key: str) -> str:
    if not pix_key:
        return ""
    if pix_key_type == PixKeyType.EMAIL:
        local, _, domain = pix_key.partition("@")
        if not domain:
            return "***"
        visible = local[:2] if len(local) > 2 else "*"
        return f"{visible}***@{domain}"
    digits = _digits_only(pix_key)
    if len(digits) <= 4:
        return "****"
    return f"{'*' * (len(digits) - 4)}{digits[-4:]}"


def map_transfer_status_to_withdrawal(asaas_status: str) -> str:
    from apps.financial.models import WithdrawalRequest

    status = (asaas_status or "").strip().upper()
    if status in ASAAS_PAID_TRANSFER_STATUSES:
        return WithdrawalRequest.Status.PAID
    if status in ASAAS_PROCESSING_TRANSFER_STATUSES:
        return WithdrawalRequest.Status.PROCESSING
    if status in {"FAILED", "CANCELLED", "REFUSED", "REJECTED"}:
        raise AsaasTransferError("A transferência Pix foi recusada pelo Asaas.")
    return WithdrawalRequest.Status.PROCESSING


def process_asaas_pix_transfer(
    *,
    value: Decimal,
    pix_key: str,
    pix_key_type: str,
    description: str = "Saque MarketChat",
    external_reference: str | None = None,
    client: AsaasClient | None = None,
) -> dict[str, Any]:
    if value <= Decimal("0"):
        raise AsaasTransferError("Valor de transferência inválido.")

    asaas_key_type = map_pix_key_type_to_asaas(pix_key_type)
    normalized_key = normalize_pix_key_for_asaas(pix_key_type, pix_key)
    ref = (external_reference or f"marketchat-withdraw-{uuid.uuid4().hex}").strip()

    body = {
        "value": float(value),
        "pixAddressKey": normalized_key,
        "pixAddressKeyType": asaas_key_type,
        "description": description[:140],
        "operationType": "PIX",
        "externalReference": ref,
    }

    logger.info(
        "Asaas transfer Pix: value=%s type=%s key=%s ref=%s",
        value,
        asaas_key_type,
        mask_pix_key_for_log(pix_key_type, normalized_key),
        ref,
    )

    asaas = client or AsaasClient()
    try:
        data = asaas.create_transfer(body)
    except AsaasAPIError as exc:
        logger.error(
            "Asaas transfer falhou: status=%s payload=%s",
            exc.status_code,
            exc.payload,
        )
        raise AsaasTransferError(format_asaas_error(exc)) from exc

    if not isinstance(data, dict):
        raise AsaasTransferError("Resposta inválida do Asaas ao criar transferência.")

    transfer_id = str(data.get("id") or "").strip()
    if not transfer_id:
        raise AsaasTransferError("O Asaas não retornou o identificador da transferência.")

    logger.info(
        "Asaas transfer criada: id=%s status=%s ref=%s",
        transfer_id,
        data.get("status"),
        ref,
    )
    return data

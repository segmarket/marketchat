"""Situação cadastral de subcontas Asaas (KYC) via webhook e consulta /myAccount/status."""

from __future__ import annotations

import logging
from typing import Any

from django.conf import settings
from django.utils import timezone

from apps.billing.models import AsaasSubaccount
from apps.billing.services.asaas_client import AsaasAPIError, AsaasClient

logger = logging.getLogger(__name__)

ACCOUNT_STATUS_EVENTS = frozenset(
    {
        "ACCOUNT_STATUS_GENERAL_APPROVAL_APPROVED",
        "ACCOUNT_STATUS_GENERAL_APPROVAL_AWAITING_APPROVAL",
        "ACCOUNT_STATUS_GENERAL_APPROVAL_PENDING",
        "ACCOUNT_STATUS_GENERAL_APPROVAL_REJECTED",
        "ACCOUNT_STATUS_COMMERCIAL_INFO_APPROVED",
        "ACCOUNT_STATUS_COMMERCIAL_INFO_AWAITING_APPROVAL",
        "ACCOUNT_STATUS_COMMERCIAL_INFO_PENDING",
        "ACCOUNT_STATUS_COMMERCIAL_INFO_REJECTED",
        "ACCOUNT_STATUS_DOCUMENT_APPROVED",
        "ACCOUNT_STATUS_DOCUMENT_AWAITING_APPROVAL",
        "ACCOUNT_STATUS_DOCUMENT_PENDING",
        "ACCOUNT_STATUS_DOCUMENT_REJECTED",
        "ACCOUNT_STATUS_BANK_ACCOUNT_INFO_APPROVED",
        "ACCOUNT_STATUS_BANK_ACCOUNT_INFO_AWAITING_APPROVAL",
        "ACCOUNT_STATUS_BANK_ACCOUNT_INFO_PENDING",
        "ACCOUNT_STATUS_BANK_ACCOUNT_INFO_REJECTED",
    },
)


def map_general_to_account_status(general: str) -> str:
    """Mapeia accountStatus.general do Asaas para AccountStatus local."""
    value = (general or "").strip().upper()
    if value == "APPROVED":
        return AsaasSubaccount.AccountStatus.APPROVED
    if value == "REJECTED":
        return AsaasSubaccount.AccountStatus.REJECTED
    return AsaasSubaccount.AccountStatus.PENDING


def build_status_message(
    *,
    general: str,
    commercial: str,
    documentation: str,
    bank: str,
) -> str:
    parts: list[str] = []
    labels = (
        ("Geral", general),
        ("Dados comerciais", commercial),
        ("Documentação", documentation),
        ("Conta bancária", bank),
    )
    for label, raw in labels:
        status = (raw or "").strip().upper()
        if status and status not in ("APPROVED", "NOT_SENT"):
            parts.append(f"{label}: {status.replace('_', ' ').title()}")
    if not parts:
        return ""
    return " · ".join(parts)


def apply_asaas_account_status_block(
    subaccount: AsaasSubaccount,
    block: dict[str, Any],
    *,
    event: str = "",
) -> bool:
    """Atualiza campos KYC a partir do objeto accountStatus do webhook ou /myAccount/status."""
    if not block:
        return False

    general = str(block.get("general") or "").strip().upper()
    commercial = str(block.get("commercialInfo") or "").strip().upper()
    documentation = str(block.get("documentation") or "").strip().upper()
    bank = str(block.get("bankAccountInfo") or "").strip().upper()

    update_fields = ["updated_at", "status_synced_at"]
    changed = False

    if general:
        subaccount.asaas_status_general = general
        update_fields.append("asaas_status_general")
        new_status = map_general_to_account_status(general)
        if subaccount.account_status != new_status:
            subaccount.account_status = new_status
            update_fields.append("account_status")
            changed = True

    if commercial:
        subaccount.asaas_status_commercial = commercial
        update_fields.append("asaas_status_commercial")
    if documentation:
        subaccount.asaas_status_documentation = documentation
        update_fields.append("asaas_status_documentation")
    if bank:
        subaccount.asaas_status_bank = bank
        update_fields.append("asaas_status_bank")

    message = build_status_message(
        general=general or subaccount.asaas_status_general,
        commercial=commercial or subaccount.asaas_status_commercial,
        documentation=documentation or subaccount.asaas_status_documentation,
        bank=bank or subaccount.asaas_status_bank,
    )
    if event.endswith("_REJECTED") and not message:
        message = event.replace("ACCOUNT_STATUS_", "").replace("_", " ").title()

    if message != subaccount.status_message:
        subaccount.status_message = message
        update_fields.append("status_message")

    subaccount.status_synced_at = timezone.now()
    subaccount.save(update_fields=list(dict.fromkeys(update_fields)))
    return changed


def _account_id_from_payload(payload: dict[str, Any]) -> str:
    account = payload.get("account")
    if isinstance(account, dict):
        return str(account.get("id") or "").strip()
    return ""


def find_subaccount_for_status_payload(payload: dict[str, Any]) -> AsaasSubaccount | None:
    account_id = _account_id_from_payload(payload)
    if account_id:
        sub = AsaasSubaccount.objects.filter(asaas_account_id=account_id).first()
        if sub:
            return sub

    wallet_id = str(payload.get("walletId") or "").strip()
    if wallet_id:
        return AsaasSubaccount.objects.filter(asaas_wallet_id=wallet_id).first()

    return None


def process_subaccount_status_webhook(*, event: str, payload: dict[str, Any]) -> bool:
    """Processa eventos ACCOUNT_STATUS_* do Asaas. Retorna True se tratou."""
    event_upper = (event or "").strip().upper()
    if event_upper not in ACCOUNT_STATUS_EVENTS:
        return False

    subaccount = find_subaccount_for_status_payload(payload)
    if subaccount is None:
        logger.info(
            "Webhook Asaas (subconta): event=%s account_id=%s sem match local",
            event_upper,
            _account_id_from_payload(payload),
        )
        return False

    block = payload.get("accountStatus")
    if not isinstance(block, dict):
        block = {}

    apply_asaas_account_status_block(subaccount, block, event=event_upper)
    logger.info(
        "Webhook Asaas (subconta): event=%s tenant=%s general=%s account_status=%s",
        event_upper,
        subaccount.tenant_id,
        subaccount.asaas_status_general,
        subaccount.account_status,
    )
    return True


def extract_subaccount_api_key(create_response: dict[str, Any]) -> str:
    """Extrai apiKey da resposta única de POST /v3/accounts."""
    token_block = create_response.get("accessToken")
    if isinstance(token_block, dict):
        key = (token_block.get("apiKey") or "").strip()
        if key:
            return key
    return str(create_response.get("apiKey") or "").strip()


def sync_subaccount_status_from_asaas(subaccount: AsaasSubaccount) -> bool:
    """
    Consulta GET /v3/myAccount/status com a apiKey da subconta (gravada na criação).
    Retorna False se não houver chave ou a API falhar.
    """
    api_key = (subaccount.asaas_subaccount_api_key or "").strip()
    if not api_key:
        logger.info(
            "sync_subaccount_status: tenant=%s sem asaas_subaccount_api_key",
            subaccount.tenant_id,
        )
        return False

    client = AsaasClient(api_key=api_key)
    try:
        data = client.get_my_account_status()
    except AsaasAPIError as exc:
        logger.warning(
            "sync_subaccount_status tenant=%s: %s",
            subaccount.tenant_id,
            exc.payload or exc,
        )
        return False

    apply_asaas_account_status_block(subaccount, data)
    return True


def subaccount_status_payload(subaccount: AsaasSubaccount) -> dict[str, Any]:
    """Campos extras expostos na API Pix para o painel."""
    return {
        "asaas_account_id": subaccount.asaas_account_id or "",
        "asaas_status_general": subaccount.asaas_status_general or "",
        "asaas_status_commercial": subaccount.asaas_status_commercial or "",
        "asaas_status_documentation": subaccount.asaas_status_documentation or "",
        "asaas_status_bank": subaccount.asaas_status_bank or "",
        "status_message": subaccount.status_message or "",
        "status_synced_at": (
            subaccount.status_synced_at.isoformat() if subaccount.status_synced_at else None
        ),
        "split_ready": bool(
            subaccount.asaas_wallet_id
            and subaccount.account_status == AsaasSubaccount.AccountStatus.APPROVED
        ),
        "can_sync_status": bool((subaccount.asaas_subaccount_api_key or "").strip()),
    }

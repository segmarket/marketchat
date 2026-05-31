from __future__ import annotations

from typing import Any

from django.conf import settings
from django.contrib.auth import get_user_model

from apps.billing.models import AsaasSubaccount
from apps.billing.services.asaas_client import AsaasAPIError, AsaasClient
from apps.billing.services.asaas_account_status import (
    ACCOUNT_STATUS_EVENTS,
    extract_subaccount_api_key,
    sync_subaccount_status_from_asaas,
)
from apps.billing.services.market_address import (
    MarketAddressParts,
    digits_only,
    market_address_is_valid_for_subaccount,
    market_address_validation_message_for_subaccount,
    parse_market_address,
)
from apps.markets.models import Market
from apps.tenants.models import Tenant

User = get_user_model()


class SubaccountSetupError(Exception):
    """Erro de validação ou integração ao configurar subconta."""


def format_asaas_error(exc: AsaasAPIError) -> str:
    payload = exc.payload
    if isinstance(payload, dict):
        errors = payload.get("errors")
        if isinstance(errors, list) and errors:
            descriptions = [
                str(item.get("description", "")).strip()
                for item in errors
                if isinstance(item, dict) and item.get("description")
            ]
            if descriptions:
                return " · ".join(descriptions[:3])
        detail = payload.get("detail")
        if isinstance(detail, str) and detail.strip():
            return detail.strip()
    return "Não foi possível concluir a operação no Asaas. Verifique os dados informados."


def get_primary_market_address(tenant_id: int) -> MarketAddressParts:
    market = Market.all_objects.filter(tenant_id=tenant_id).order_by("name").first()
    if market is None:
        return MarketAddressParts()
    return parse_market_address(market.address)


def _resolve_mobile_phone(tenant: Tenant, user: User) -> str:
    for raw in (tenant.phone, getattr(user, "phone", "")):
        digits = digits_only(raw or "")
        if len(digits) >= 10:
            return f"{digits[:2]} {digits[2:]}"
    raise SubaccountSetupError(
        "Informe um telefone válido em Configurações → Minha Conta antes de configurar o Pix.",
    )


def _asaas_is_production() -> bool:
    url = (getattr(settings, "ASAAS_API_URL", "") or "").lower()
    return "sandbox" not in url and "api-sandbox" not in url


def build_asaas_subaccount_payload(
    subaccount: AsaasSubaccount,
    tenant: Tenant,
    user: User,
    market_parts: MarketAddressParts,
) -> dict[str, Any]:
    msg = market_address_validation_message_for_subaccount(market_parts)
    if msg:
        raise SubaccountSetupError(msg)

    doc = digits_only(subaccount.cpf_cnpj)
    if len(doc) not in (11, 14):
        raise SubaccountSetupError("Informe um CPF (11 dígitos) ou CNPJ (14 dígitos) válido.")

    if _asaas_is_production() and len(doc) != 14:
        raise SubaccountSetupError(
            "Em produção o Asaas exige CNPJ (14 dígitos) para criar subconta de recebimento Pix.",
        )

    body: dict[str, Any] = {
        "name": subaccount.name.strip(),
        "email": subaccount.email.strip(),
        "cpfCnpj": doc,
        "mobilePhone": _resolve_mobile_phone(tenant, user),
        "incomeValue": float(settings.ASAAS_SUBACCOUNT_INCOME_VALUE),
        "address": market_parts.street.strip(),
        "addressNumber": market_parts.number.strip(),
        "province": market_parts.neighborhood.strip(),
        "postalCode": digits_only(market_parts.cep),
        "state": (market_parts.state or "").strip().upper()[:2],
    }
    if market_parts.complement.strip():
        body["complement"] = market_parts.complement.strip()
    if len(doc) == 14:
        company_type = (
            getattr(settings, "ASAAS_SUBACCOUNT_COMPANY_TYPE", None) or "MEI"
        ).strip().upper()
        body["companyType"] = company_type

    webhooks = _build_subaccount_webhooks(subaccount.email)
    if webhooks:
        body["webhooks"] = webhooks

    return body


def _build_subaccount_webhooks(notify_email: str) -> list[dict[str, Any]]:
    """Registra webhook de status na subconta (mesma URL/token da conta raiz)."""
    base = (getattr(settings, "PUBLIC_WEBHOOK_BASE_URL", "") or "").strip().rstrip("/")
    token = (getattr(settings, "ASAAS_WEBHOOK_TOKEN", "") or "").strip()
    if not base or not token or len(token) < 32:
        return []

    url = f"{base}/api/billing/webhooks/asaas/"
    email = (
        getattr(settings, "ASAAS_WEBHOOK_NOTIFY_EMAIL", "") or notify_email or ""
    ).strip()
    if not email:
        return []

    status_events = sorted(ACCOUNT_STATUS_EVENTS)
    return [
        {
            "name": "MarketChat Subconta Status",
            "url": url,
            "email": email,
            "enabled": True,
            "interrupted": False,
            "apiVersion": 3,
            "authToken": token,
            "sendType": "NON_SEQUENTIALLY",
            "events": status_events,
        }
    ]


def create_tenant_subaccount(subaccount: AsaasSubaccount) -> AsaasSubaccount:
    if subaccount.asaas_wallet_id:
        return subaccount

    tenant = subaccount.tenant
    user = (
        User.objects.filter(tenant_id=tenant.id, is_tenant_admin=True)
        .order_by("id")
        .first()
    )
    if user is None:
        user = User.objects.filter(tenant_id=tenant.id).order_by("id").first()
    if user is None:
        raise SubaccountSetupError("Nenhum usuário encontrado para o tenant.")

    market_parts = get_primary_market_address(tenant.id)
    if not market_address_is_valid_for_subaccount(market_parts):
        msg = market_address_validation_message_for_subaccount(market_parts)
        raise SubaccountSetupError(msg or "Endereço do mercado inválido.")

    payload = build_asaas_subaccount_payload(subaccount, tenant, user, market_parts)
    client = AsaasClient()
    try:
        data = client.create_subaccount(payload)
    except AsaasAPIError as exc:
        raise SubaccountSetupError(format_asaas_error(exc)) from exc

    wallet_id = (data.get("walletId") or "").strip()
    account_id = (data.get("id") or "").strip()
    if not wallet_id:
        raise SubaccountSetupError("O Asaas não retornou o identificador da subconta (walletId).")

    subaccount.asaas_wallet_id = wallet_id
    subaccount.asaas_account_id = account_id
    subaccount.asaas_subaccount_api_key = extract_subaccount_api_key(data)
    subaccount.account_status = AsaasSubaccount.AccountStatus.PENDING
    subaccount.asaas_status_general = "AWAITING_APPROVAL"
    subaccount.status_message = (
        "Subconta criada. Aguardando aprovação do Asaas para liberar split Pix (100% na subconta)."
    )
    subaccount.save(
        update_fields=[
            "asaas_wallet_id",
            "asaas_account_id",
            "asaas_subaccount_api_key",
            "account_status",
            "asaas_status_general",
            "status_message",
            "updated_at",
        ],
    )

    sync_subaccount_status_from_asaas(subaccount)
    subaccount.refresh_from_db()
    return subaccount

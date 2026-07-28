"""Customer Asaas Consumidor Final por tenant (PIX avulso no chat)."""

from __future__ import annotations

import logging

from apps.billing.services.asaas_client import AsaasAPIError, AsaasClient
from apps.billing.services.asaas_errors import format_asaas_error
from apps.tenants.models import Tenant

logger = logging.getLogger(__name__)


class TenantDefaultCustomerError(Exception):
    pass


def _digits_only(value: str) -> str:
    return "".join(c for c in (value or "") if c.isdigit())


def tenant_has_valid_billing_document(tenant: Tenant) -> bool:
    cpf_cnpj = _digits_only(tenant.cpf_cnpj)
    return len(cpf_cnpj) in (11, 14)


def resident_billing_identified(resident) -> bool:
    """Morador com cadastro completo para cobrança nominal no Asaas."""
    name = (getattr(resident, "name", None) or "").strip()
    market_id = getattr(resident, "market_id", None)
    return bool(name and market_id)


def ensure_tenant_default_asaas_customer(
    tenant: Tenant,
    *,
    client: AsaasClient | None = None,
) -> str:
    """
    Garante customer Asaas Consumidor Final no tenant.
    Idempotente: reutiliza asaas_default_customer_id se já existir.
    """
    existing = (tenant.asaas_default_customer_id or "").strip()
    if existing:
        return existing

    if not tenant_has_valid_billing_document(tenant):
        raise TenantDefaultCustomerError(
            "Cadastre o CPF ou CNPJ da empresa em Configurações da conta "
            "para habilitar cobranças PIX avulsas no chat.",
        )

    client = client or AsaasClient()
    cpf_cnpj = _digits_only(tenant.cpf_cnpj)
    display_name = f"Consumidor Final - {tenant.name}".strip()[:100]
    body = {
        "name": display_name,
        "cpfCnpj": cpf_cnpj,
        "notificationDisabled": True,
    }
    try:
        data = client.create_customer(body)
    except AsaasAPIError as exc:
        raise TenantDefaultCustomerError(format_asaas_error(exc)) from exc

    customer_id = str(data.get("id") or "").strip()
    if not customer_id:
        raise TenantDefaultCustomerError("Asaas não retornou o cliente Consumidor Final.")

    tenant.asaas_default_customer_id = customer_id
    tenant.save(update_fields=["asaas_default_customer_id", "updated_at"])
    logger.info(
        "Consumidor Final Asaas provisionado: tenant_id=%s customer=%s",
        tenant.pk,
        customer_id,
    )
    return customer_id


def ensure_tenant_default_asaas_customer_by_id(
    tenant_id: int,
    *,
    client: AsaasClient | None = None,
) -> str | None:
    """Best-effort para hooks; loga falha sem propagar."""
    tenant = Tenant.objects.filter(pk=tenant_id).first()
    if tenant is None:
        return None
    try:
        return ensure_tenant_default_asaas_customer(tenant, client=client)
    except TenantDefaultCustomerError as exc:
        logger.warning(
            "Falha ao provisionar Consumidor Final: tenant_id=%s %s",
            tenant_id,
            exc,
        )
        return None

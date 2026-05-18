from __future__ import annotations

from typing import Any

from django.core.cache import cache

from apps.billing.models import Subscription
from apps.billing.services.asaas_client import AsaasClient
from apps.tenants.models import Tenant

CACHE_TTL_SECONDS = 300
CACHE_KEY_PREFIX = "billing:history:"

# Asaas payment status -> API status for the front-end
_STATUS_MAP: dict[str, str] = {
    "RECEIVED": "PAID",
    "CONFIRMED": "PAID",
    "RECEIVED_IN_CASH": "PAID",
    "PENDING": "PENDING",
    "OVERDUE": "OVERDUE",
}


def _cache_key(tenant_id: int) -> str:
    return f"{CACHE_KEY_PREFIX}{tenant_id}"


def invalidate_billing_history_cache(tenant_id: int) -> None:
    cache.delete(_cache_key(tenant_id))


def _map_payment_status(raw: str | None) -> str | None:
    if not raw:
        return None
    upper = raw.upper()
    if upper in _STATUS_MAP:
        return _STATUS_MAP[upper]
    return "PENDING"


def _map_payment(payment: dict[str, Any]) -> dict[str, Any] | None:
    status = _map_payment_status(payment.get("status"))
    if status is None:
        return None
    return {
        "due_date": payment.get("dueDate"),
        "value": payment.get("value"),
        "status": status,
        "billing_type": payment.get("billingType"),
        "invoice_url": payment.get("invoiceUrl") or "",
    }


def get_billing_history_for_tenant(
    tenant: Tenant,
    *,
    client: AsaasClient | None = None,
) -> list[dict[str, Any]]:
    """Lista cobranças do tenant no Asaas (com cache de 5 minutos)."""
    cache_key = _cache_key(tenant.pk)
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    try:
        subscription = tenant.subscription
    except Subscription.DoesNotExist:
        return []

    client = client or AsaasClient()
    response = client.list_payments(
        customer=subscription.asaas_customer_id,
        limit=100,
    )
    items = response.get("data") or []
    history: list[dict[str, Any]] = []
    for payment in items:
        if not isinstance(payment, dict):
            continue
        mapped = _map_payment(payment)
        if mapped is not None:
            history.append(mapped)

    history.sort(key=lambda row: row.get("due_date") or "", reverse=True)
    cache.set(cache_key, history, CACHE_TTL_SECONDS)
    return history

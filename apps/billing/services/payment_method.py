from __future__ import annotations

from typing import Any, Mapping

from apps.billing.models import Subscription
from apps.billing.services.asaas_client import AsaasClient
from apps.billing.services.billing_history import invalidate_billing_history_cache
from apps.tenants.models import Tenant

_BILLING_TYPE_LABELS: dict[str, str] = {
    "BOLETO": "Boleto bancário",
    "PIX": "Pix",
    "CREDIT_CARD": "Cartão de crédito",
    "DEBIT_CARD": "Cartão de débito",
    "UNDEFINED": "Não definido",
}

_CARD_BRAND_LABELS: dict[str, str] = {
    "VISA": "Visa",
    "MASTERCARD": "Mastercard",
    "ELO": "Elo",
    "AMEX": "American Express",
    "HIPERCARD": "Hipercard",
    "DINERS": "Diners",
    "DISCOVER": "Discover",
}


def _subscription_for_tenant(tenant: Tenant) -> Subscription:
    try:
        return tenant.subscription
    except Subscription.DoesNotExist as exc:
        raise ValueError("Assinatura não encontrada para este tenant.") from exc


def _brand_label(brand: str | None) -> str:
    if not brand:
        return "Cartão"
    key = brand.upper().replace(" ", "_")
    return _CARD_BRAND_LABELS.get(key, brand.title())


def _last_four(card_number: str | None) -> str | None:
    if not card_number:
        return None
    digits = "".join(c for c in card_number if c.isdigit())
    if len(digits) >= 4:
        return digits[-4:]
    return digits or None


def get_payment_method_summary(
    tenant: Tenant,
    *,
    client: AsaasClient | None = None,
) -> dict[str, Any]:
    subscription = _subscription_for_tenant(tenant)
    client = client or AsaasClient()
    sub_data = client.get_subscription(subscription.asaas_subscription_id)
    billing_type = (sub_data.get("billingType") or "").upper()
    asaas_status = (sub_data.get("status") or "").upper()
    tenant_status = tenant.subscription_status
    local_canceled = tenant_status == Tenant.SubscriptionStatus.CANCELED
    in_trial = not tenant.is_trial_period_over()

    active_markets = tenant.active_markets_count()
    unit_price = tenant.subscription_unit_value()
    base: dict[str, Any] = {
        "next_due_date": sub_data.get("nextDueDate"),
        "asaas_status": asaas_status,
        "subscription_status": tenant_status,
        "subscription_canceled": local_canceled,
        "can_cancel": not local_canceled and asaas_status == "ACTIVE",
        "can_reactivate": local_canceled and active_markets > 0,
        "in_trial_period": in_trial,
        "trial_ends_at": tenant.trial_ends_at.date().isoformat(),
        "active_markets_count": active_markets,
        "monthly_total": round(active_markets * unit_price, 2),
        "unit_price": unit_price,
        "is_in_grace_period": tenant.is_in_grace_period(),
    }

    if billing_type == "CREDIT_CARD":
        brand = sub_data.get("creditCardBrand") or ""
        last_four = _last_four(sub_data.get("creditCardNumber"))
        brand_label = _brand_label(brand)
        if last_four:
            display = f"{brand_label} terminando em {last_four}"
        else:
            display = brand_label
        return {
            **base,
            "billing_type": billing_type,
            "card_brand": brand.upper() if brand else None,
            "card_last_four": last_four,
            "display_label": display,
        }

    label = _BILLING_TYPE_LABELS.get(billing_type, billing_type or "Cobrança")
    return {
        **base,
        "billing_type": billing_type or "UNDEFINED",
        "card_brand": None,
        "card_last_four": None,
        "display_label": label,
    }


def update_subscription_card(
    tenant: Tenant,
    credit_card: Mapping[str, Any],
    credit_card_holder_info: Mapping[str, Any],
    remote_ip: str,
    *,
    client: AsaasClient | None = None,
) -> dict[str, Any]:
    subscription = _subscription_for_tenant(tenant)
    client = client or AsaasClient()
    customer_id = subscription.asaas_customer_id

    token_payload = {
        "customer": customer_id,
        "creditCard": dict(credit_card),
    }
    token_resp = client.tokenize_credit_card(token_payload)
    credit_card_token = token_resp.get("creditCardToken") or token_resp.get("token")
    if not credit_card_token:
        raise ValueError("Resposta de tokenização Asaas sem creditCardToken")

    update_body: dict[str, Any] = {
        "creditCardToken": credit_card_token,
        "creditCardHolderInfo": dict(credit_card_holder_info),
        "remoteIp": remote_ip or "127.0.0.1",
    }
    client.update_subscription_credit_card(
        subscription.asaas_subscription_id,
        update_body,
    )
    invalidate_billing_history_cache(tenant.pk)
    return get_payment_method_summary(tenant, client=client)

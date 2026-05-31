from __future__ import annotations

from datetime import timedelta
from typing import Any, Mapping

from django.conf import settings
from django.utils import timezone

from apps.accounts.models import User
from apps.billing.models import Subscription
from apps.billing.services.asaas_client import AsaasClient
from apps.tenants.models import Tenant


def _next_due_date_iso() -> str:
    day = timezone.now().date() + timedelta(days=settings.TRIAL_DAYS)
    return day.isoformat()


def create_trial_subscription(
    tenant: Tenant,
    user: User,
    credit_card: Mapping[str, Any],
    credit_card_holder_info: Mapping[str, Any],
    remote_ip: str,
    client: AsaasClient | None = None,
) -> Subscription:
    """
    Cria customer + token de cartão + assinatura no Asaas (primeiro vencimento em TRIAL_DAYS).
    Persiste Subscription ligada ao tenant.
    """
    client = client or AsaasClient()
    customer_payload: dict[str, Any] = {
        "name": tenant.name,
        "email": user.email,
    }
    cpf = credit_card_holder_info.get("cpfCnpj")
    if cpf:
        customer_payload["cpfCnpj"] = cpf

    customer = client.create_customer(customer_payload)
    customer_id = customer["id"]

    token_payload = {
        "customer": customer_id,
        "creditCard": dict(credit_card),
        "creditCardHolderInfo": dict(credit_card_holder_info),
        "remoteIp": remote_ip or "127.0.0.1",
    }
    token_resp = client.tokenize_credit_card(token_payload)
    credit_card_token = token_resp.get("creditCardToken") or token_resp.get("token")
    if not credit_card_token:
        raise ValueError("Resposta de tokenização Asaas sem creditCardToken")

    subscription_payload = {
        "customer": customer_id,
        "billingType": "CREDIT_CARD",
        "value": float(settings.DEFAULT_SUBSCRIPTION_VALUE),
        "nextDueDate": _next_due_date_iso(),
        "cycle": "MONTHLY",
        "creditCardToken": credit_card_token,
        "creditCardHolderInfo": dict(credit_card_holder_info),
        "remoteIp": remote_ip or "127.0.0.1",
    }
    sub_resp = client.create_subscription(subscription_payload)
    subscription_id = sub_resp["id"]
    raw_status = (sub_resp.get("status") or "ACTIVE").upper()
    try:
        sub_status = Subscription.Status(raw_status)
    except ValueError:
        sub_status = Subscription.Status.ACTIVE

    tenant_updates: list[str] = []
    cpf = (credit_card_holder_info.get("cpfCnpj") or "").strip()
    if cpf:
        tenant.cpf_cnpj = cpf
        tenant_updates.append("cpf_cnpj")
    phone = (credit_card_holder_info.get("phone") or "").strip()
    if phone:
        tenant.phone = phone
        tenant_updates.append("phone")
    if tenant_updates:
        tenant_updates.append("updated_at")
        tenant.save(update_fields=tenant_updates)

    return Subscription.objects.create(
        tenant=tenant,
        asaas_customer_id=str(customer_id),
        asaas_subscription_id=str(subscription_id),
        status=sub_status,
        trial_ends_at=tenant.trial_ends_at,
    )

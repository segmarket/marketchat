from __future__ import annotations

from datetime import timedelta

from django.utils import timezone

from apps.billing.models import Subscription
from apps.billing.services.asaas_client import AsaasAPIError, AsaasClient
from apps.billing.services.payment_method import _subscription_for_tenant
from apps.billing.services.subscription_charges import outstanding_charges
from apps.tenants.models import Tenant


class ReactivationError(Exception):
    """Erro de negócio na reativação (sem mercados, status inválido)."""


class ReactivationCardError(Exception):
    """Gateway rejeitou o cartão salvo; o cliente deve cadastrar um novo."""


class ReactivationDebtError(ReactivationError):
    """Cancelada com fatura em atraso: reativar não pode apagar a pendência."""


def _next_due_date_iso() -> str:
    return (timezone.now().date() + timedelta(days=1)).isoformat()


def _recoverable_asaas_status(status: str) -> bool:
    return status.upper() in {"ACTIVE", "INACTIVE", "EXPIRED"}


def reactivate_tenant_subscription(
    tenant: Tenant,
    *,
    client: AsaasClient | None = None,
) -> Subscription:
    """
    Reativa assinatura cancelada manualmente: tenta reativar no Asaas ou cria nova
    assinatura no mesmo customer, com valor = mercados ativos × preço unitário.
    """
    if tenant.subscription_status != Tenant.SubscriptionStatus.CANCELED:
        raise ReactivationError("A assinatura não está cancelada.")

    value = tenant.computed_subscription_value()
    if value <= 0:
        raise ReactivationError(
            "É necessário ter pelo menos um mercado ativo para reativar a assinatura.",
        )

    subscription = _subscription_for_tenant(tenant)
    if tenant.overdue_since is not None or outstanding_charges(subscription).exists():
        raise ReactivationDebtError(
            "A assinatura foi cancelada com fatura em atraso. "
            "Fale com o suporte para regularizar antes de reativar.",
        )
    client = client or AsaasClient()
    customer_id = subscription.asaas_customer_id
    subscription_id = subscription.asaas_subscription_id

    try:
        existing = client.get_subscription(subscription_id)
        asaas_status = (existing.get("status") or "").upper()
        if _recoverable_asaas_status(asaas_status):
            client.update_subscription(
                subscription_id,
                {
                    "status": "ACTIVE",
                    "value": value,
                    "updatePendingPayments": True,
                },
            )
        else:
            raise AsaasAPIError("Assinatura não recuperável", status_code=404)
    except AsaasAPIError as exc:
        if exc.status_code not in (404, None) and exc.status_code != 400:
            if _is_card_error(exc):
                raise ReactivationCardError(
                    "Não foi possível reativar com o cartão atual.",
                ) from exc
            raise
        try:
            new_sub = client.create_subscription(
                {
                    "customer": customer_id,
                    "billingType": "CREDIT_CARD",
                    "cycle": "MONTHLY",
                    "value": value,
                    "nextDueDate": _next_due_date_iso(),
                },
            )
        except AsaasAPIError as create_exc:
            if _is_card_error(create_exc):
                raise ReactivationCardError(
                    "Não foi possível reativar com o cartão atual.",
                ) from create_exc
            raise

        new_id = new_sub.get("id")
        if not new_id:
            raise AsaasAPIError("Resposta Asaas sem id de assinatura")
        subscription.asaas_subscription_id = str(new_id)
        subscription.save(update_fields=["asaas_subscription_id", "updated_at"])

    subscription.status = Subscription.Status.ACTIVE
    subscription.save(update_fields=["status", "updated_at"])

    tenant.billing_blocked_at = None
    tenant.subscription_status = Tenant.SubscriptionStatus.ACTIVE
    tenant.overdue_since = None
    tenant.whatsapp_logout_pending_since = None
    tenant.save(
        update_fields=[
            "subscription_status",
            "overdue_since",
            "billing_blocked_at",
            "whatsapp_logout_pending_since",
            "updated_at",
        ],
    )

    return subscription


def _is_card_error(exc: AsaasAPIError) -> bool:
    if exc.status_code in (402, 422):
        return True
    payload = exc.payload
    if not isinstance(payload, dict):
        return False
    errors = payload.get("errors")
    if not isinstance(errors, list):
        return False
    for item in errors:
        if not isinstance(item, dict):
            continue
        code = str(item.get("code", "")).lower()
        desc = str(item.get("description", "")).lower()
        if "card" in code or "cartão" in desc or "credit" in desc:
            return True
    return exc.status_code == 400

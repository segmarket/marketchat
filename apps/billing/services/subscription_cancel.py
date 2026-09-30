from __future__ import annotations

from django.utils import timezone

from apps.billing.models import Subscription
from apps.billing.services.asaas_client import AsaasClient
from apps.billing.services.payment_method import _subscription_for_tenant
from apps.tenants.models import Tenant


def _apply_local_cancellation(tenant: Tenant, subscription: Subscription) -> None:
    subscription.status = Subscription.Status.CANCELLED
    subscription.save(update_fields=["status", "updated_at"])

    tenant.subscription_status = Tenant.SubscriptionStatus.CANCELED
    update_fields = ["subscription_status", "updated_at"]
    if tenant.is_trial_period_over():
        if tenant.billing_blocked_at is None:
            now = timezone.now()
            tenant.billing_blocked_at = now
            tenant.whatsapp_logout_pending_since = tenant.whatsapp_logout_pending_since or now
            update_fields += ["billing_blocked_at", "whatsapp_logout_pending_since"]
    tenant.save(update_fields=update_fields)


def cancel_tenant_subscription(
    tenant: Tenant,
    *,
    client: AsaasClient | None = None,
) -> None:
    """
    Cancela a assinatura no Asaas e atualiza o estado local.
    Durante o trial o painel permanece liberado até trial_ends_at.
    """
    subscription = _subscription_for_tenant(tenant)
    if subscription.status == Subscription.Status.CANCELLED:
        return
    if tenant.subscription_status == Tenant.SubscriptionStatus.CANCELED:
        return

    client = client or AsaasClient()
    client.cancel_subscription(subscription.asaas_subscription_id)
    _apply_local_cancellation(tenant, subscription)

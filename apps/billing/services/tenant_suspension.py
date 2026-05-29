from __future__ import annotations

import logging

from apps.billing.services.subscription_enforcement import enforce_tenant_suspension
from apps.tenants.models import Tenant

logger = logging.getLogger(__name__)


def suspend_tenant_for_overdue(tenant: Tenant) -> None:
    """Suspende tenant inadimplente (após carência) e desconecta WhatsApp via logout Evolution."""
    if tenant.subscription_status == Tenant.SubscriptionStatus.SUSPENDED:
        return
    enforce_tenant_suspension(tenant, reason="billing_overdue", send_email=False)


def tenant_has_messaging_access(tenant_id: int) -> bool:
    """Bloqueia processamento de mensagens WhatsApp para tenant suspenso ou trial vencido."""
    tenant = Tenant.objects.filter(pk=tenant_id).only(
        "subscription_status",
        "trial_ends_at",
        "overdue_since",
        "billing_blocked_at",
    ).first()
    if tenant is None:
        return False
    if tenant.subscription_status == Tenant.SubscriptionStatus.SUSPENDED:
        return False
    if tenant.billing_blocked_at is not None:
        return False
    if (
        tenant.subscription_status == Tenant.SubscriptionStatus.TRIAL
        and tenant.is_trial_period_over()
    ):
        return False
    if tenant.subscription_status == Tenant.SubscriptionStatus.OVERDUE:
        return tenant.is_in_grace_period()
    return True

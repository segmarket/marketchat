from __future__ import annotations

import logging

from apps.billing.services.subscription_enforcement import enforce_tenant_suspension
from apps.tenants.models import Tenant

logger = logging.getLogger(__name__)


def suspend_tenant_for_overdue(tenant: Tenant) -> None:
    """
    Suspende localmente o tenant inadimplente após a carência (chamado no caminho da request).
    O logout Evolution e o e-mail de suspensão ficam pendentes para o check_subscriptions.
    """
    if tenant.subscription_status == Tenant.SubscriptionStatus.SUSPENDED:
        return
    enforce_tenant_suspension(
        tenant,
        reason="billing_overdue",
        send_email=False,
        attempt_logout=False,
    )


def tenant_has_messaging_access(tenant_id: int) -> bool:
    """Bot WhatsApp: bloqueado para suspenso, bloqueado, trial/cancelado após o trial ou fora da carência."""
    tenant = Tenant.objects.filter(pk=tenant_id).only(
        "subscription_status",
        "trial_ends_at",
        "overdue_since",
        "billing_blocked_at",
    ).first()
    if tenant is None:
        return False
    return tenant.has_messaging_access()

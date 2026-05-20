"""Regras de acesso ao painel administrativo por tenant."""

from __future__ import annotations

from apps.tenants.models import Tenant

TRIAL_EXPIRED_MESSAGE = "Seu período de testes de 7 dias terminou."
BILLING_SUSPENDED_MESSAGE = (
    "Acesso suspenso por pendência financeira. Regularize o pagamento para continuar."
)


def get_panel_access_denial(tenant: Tenant) -> tuple[str, str] | None:
    if tenant.has_panel_access():
        return None
    if tenant.subscription_status in (
        Tenant.SubscriptionStatus.SUSPENDED,
        Tenant.SubscriptionStatus.OVERDUE,
    ) or tenant.billing_blocked_at is not None:
        return ("billing_suspended", BILLING_SUSPENDED_MESSAGE)
    if tenant.is_trial_period_over():
        return ("trial_expired", TRIAL_EXPIRED_MESSAGE)
    return ("billing_suspended", BILLING_SUSPENDED_MESSAGE)

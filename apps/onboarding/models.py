from django.db import models

from apps.tenants.models import Tenant


class TenantOnboarding(models.Model):
    """Progresso da jornada de setup gamificada por tenant."""

    tenant = models.OneToOneField(
        Tenant,
        on_delete=models.CASCADE,
        related_name="onboarding",
    )
    step_market_created = models.BooleanField(default=False)
    step_product_created = models.BooleanField(default=False)
    step_whatsapp_connected = models.BooleanField(default=False)
    step_test_order_completed = models.BooleanField(default=False)
    onboarding_finished = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Onboarding do tenant"
        verbose_name_plural = "Onboardings dos tenants"

    def __str__(self) -> str:
        return f"Onboarding tenant={self.tenant_id}"

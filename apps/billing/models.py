from django.db import models
from django.utils import timezone

from apps.tenants.models import Tenant


class Subscription(models.Model):
    """Assinatura Asaas vinculada ao tenant."""

    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Ativa"
        INACTIVE = "INACTIVE", "Inativa"
        OVERDUE = "OVERDUE", "Em atraso"
        CANCELLED = "CANCELLED", "Cancelada"

    tenant = models.OneToOneField(
        Tenant,
        on_delete=models.CASCADE,
        related_name="subscription",
    )
    asaas_customer_id = models.CharField(max_length=64)
    asaas_subscription_id = models.CharField(max_length=64)
    status = models.CharField(
        max_length=32,
        choices=Status.choices,
        default=Status.ACTIVE,
    )
    trial_ends_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Subscription({self.asaas_subscription_id})"

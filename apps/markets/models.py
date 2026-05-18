from django.db import models

from apps.tenants.models import TenantAwareModel


class Market(TenantAwareModel):
    """Mercado autônomo em condomínio (escopo por tenant)."""

    class Status(models.TextChoices):
        ACTIVE = "active", "Ativo"
        INACTIVE = "inactive", "Inativo"

    name = models.CharField(max_length=255)
    address = models.TextField()
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.ACTIVE,
    )

    class Meta:
        ordering = ["name"]
        indexes = [
            models.Index(fields=["tenant", "status"]),
        ]

    def __str__(self) -> str:
        return self.name

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
    custom_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Preço mensal negociado. Vazio = MARKET_MONTHLY_PRICE.",
    )

    class Meta:
        ordering = ["name"]
        indexes = [
            models.Index(fields=["tenant", "status"]),
        ]

    def __str__(self) -> str:
        return self.name

    def monthly_unit_price(self) -> float:
        """Preço deste mercado na assinatura (custom ou padrão do plano)."""
        if self.custom_price is not None:
            return float(self.custom_price)
        from django.conf import settings

        return float(getattr(settings, "MARKET_MONTHLY_PRICE", 59.90))

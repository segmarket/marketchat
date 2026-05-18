from django.db import models

from apps.markets.models import Market
from apps.tenants.models import TenantAwareModel


class Notification(TenantAwareModel):
    """Alerta exibido no painel administrativo (por tenant)."""

    class Severity(models.TextChoices):
        CRITICAL = "CRITICAL", "Crítico"
        WARNING = "WARNING", "Aviso"
        INFO = "INFO", "Informação"

    market = models.ForeignKey(
        Market,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="notifications",
    )
    title = models.CharField(max_length=120)
    message = models.TextField()
    severity = models.CharField(
        max_length=16,
        choices=Severity.choices,
        default=Severity.INFO,
        db_index=True,
    )
    is_read = models.BooleanField(default=False, db_index=True)
    intent_type = models.CharField(max_length=32, blank=True, default="")

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["tenant", "is_read", "-created_at"]),
            models.Index(fields=["tenant", "is_read"]),
        ]

    def __str__(self) -> str:
        return f"{self.title} ({self.severity})"

from django.db import models

from apps.tenants.models import TenantAwareModel


class WhatsappInstance(TenantAwareModel):
    """Instância WhatsApp provisionada no Evolution GO (uma por tenant no MVP)."""

    class ConnectionStatus(models.TextChoices):
        UNKNOWN = "unknown", "Desconhecido"
        CONNECTING = "connecting", "Conectando"
        OPEN = "open", "Conectado"
        CLOSE = "close", "Desconectado"

    class Platform(models.TextChoices):
        UNKNOWN = "unknown", "Desconhecido"
        ANDROID = "android", "Android"
        IOS = "ios", "iOS"

    instance_name = models.CharField(max_length=255)
    instance_id = models.CharField(max_length=64, blank=True, default="")
    api_key = models.CharField(max_length=512, blank=True, default="")
    webhook_url = models.URLField(max_length=2048, blank=True, default="")
    webhook_secret = models.CharField(max_length=255, blank=True, default="")
    pair_phone = models.CharField(max_length=32, blank=True, default="")
    connection_status = models.CharField(
        max_length=32,
        choices=ConnectionStatus.choices,
        default=ConnectionStatus.UNKNOWN,
    )
    is_active = models.BooleanField(default=True)
    last_webhook_at = models.DateTimeField(null=True, blank=True)
    profile_name = models.CharField(max_length=255, blank=True, default="")
    profile_picture_url = models.TextField(blank=True, default="")
    phone_number = models.CharField(max_length=32, blank=True, default="")
    platform = models.CharField(
        max_length=16,
        choices=Platform.choices,
        default=Platform.UNKNOWN,
    )
    disconnect_reason = models.CharField(max_length=512, blank=True, default="")

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["tenant"],
                name="uniq_whatsappinstance_tenant",
            ),
        ]
        indexes = [
            models.Index(fields=["tenant", "instance_name"]),
            models.Index(fields=["instance_name"]),
            models.Index(fields=["instance_id"]),
        ]

    def __str__(self) -> str:
        return f"{self.instance_name} (tenant={self.tenant_id})"

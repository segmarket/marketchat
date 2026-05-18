import uuid

from django.db import models

from apps.tenants.models import Tenant, TenantAwareModel


class Product(TenantAwareModel):
    """Produto do catálogo do mercado (escopo por tenant)."""

    class Status(models.TextChoices):
        ACTIVE = "active", "Ativo"
        INACTIVE = "inactive", "Inativo"

    sku = models.CharField(max_length=64)
    name = models.CharField(max_length=255)
    search_aliases = models.TextField(
        blank=True,
        default="",
        help_text="Sinônimos de busca (vírgula ou quebra de linha).",
    )
    price = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.ACTIVE,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "sku"],
                name="uniq_product_tenant_sku",
            ),
        ]
        indexes = [
            models.Index(fields=["tenant", "sku"]),
            models.Index(fields=["tenant", "status"]),
        ]
        ordering = ["sku"]

    def __str__(self) -> str:
        return f"{self.sku} — {self.name}"


class ProductImportSession(models.Model):
    """Staging de importação em massa (preview → confirm)."""

    tenant = models.ForeignKey(
        Tenant,
        on_delete=models.CASCADE,
        related_name="product_import_sessions",
    )
    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    payload = models.JSONField(default=list)
    new_count = models.PositiveIntegerField(default=0)
    updated_count = models.PositiveIntegerField(default=0)
    expires_at = models.DateTimeField()
    confirmed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["tenant", "token"]),
            models.Index(fields=["expires_at"]),
        ]

    def __str__(self) -> str:
        return f"import:{self.token} (tenant={self.tenant_id})"

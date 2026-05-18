from django.db import models
from django.utils import timezone

from apps.tenants.managers import TenantManager


class Tenant(models.Model):
    """Conta / empresa do cliente."""

    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=80, unique=True)
    phone = models.CharField(max_length=32, blank=True, default="")
    cpf_cnpj = models.CharField(max_length=18, blank=True, default="")
    trial_ends_at = models.DateTimeField()
    billing_blocked_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def block_billing_access(self) -> None:
        self.billing_blocked_at = timezone.now()
        self.save(update_fields=["billing_blocked_at", "updated_at"])

    def clear_billing_block(self) -> None:
        self.billing_blocked_at = None
        self.save(update_fields=["billing_blocked_at", "updated_at"])

    def has_billing_access(self) -> bool:
        if self.billing_blocked_at is not None:
            return False
        return True

    def __str__(self) -> str:
        return self.name


class TenantAwareModel(models.Model):
    """Herde deste modelo para dados escopados por tenant."""

    tenant = models.ForeignKey(
        Tenant,
        on_delete=models.CASCADE,
        related_name="%(class)ss",
        db_index=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = TenantManager()
    all_objects = models.Manager()

    class Meta:
        abstract = True


class DemoNote(TenantAwareModel):
    """Recurso de exemplo para testes de isolamento entre tenants."""

    title = models.CharField(max_length=200)

    class Meta:
        ordering = ["-created_at"]

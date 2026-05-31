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


class AsaasSubaccount(models.Model):
    """Subconta Asaas do tenant para recebimentos Pix (split/transferências)."""

    class PixKeyType(models.TextChoices):
        CPF = "CPF", "CPF"
        CNPJ = "CNPJ", "CNPJ"
        EMAIL = "EMAIL", "E-mail"
        PHONE = "PHONE", "Celular"
        RANDOM = "RANDOM", "Chave aleatória"

    class AccountStatus(models.TextChoices):
        PENDING = "PENDING", "Em análise"
        APPROVED = "APPROVED", "Aprovada"
        REJECTED = "REJECTED", "Rejeitada"

    tenant = models.OneToOneField(
        Tenant,
        on_delete=models.CASCADE,
        related_name="asaas_subaccount",
    )
    name = models.CharField(max_length=255)
    email = models.EmailField()
    cpf_cnpj = models.CharField(max_length=18)
    pix_key_type = models.CharField(max_length=16, choices=PixKeyType.choices)
    pix_key = models.CharField(max_length=255)
    asaas_wallet_id = models.CharField(max_length=64, blank=True, default="")
    asaas_account_id = models.CharField(max_length=64, blank=True, default="", db_index=True)
    # Chave da subconta (retornada uma vez no POST /accounts); usada só para GET /myAccount/status.
    asaas_subaccount_api_key = models.CharField(max_length=255, blank=True, default="")
    account_status = models.CharField(
        max_length=16,
        choices=AccountStatus.choices,
        default=AccountStatus.PENDING,
    )
    asaas_status_general = models.CharField(max_length=32, blank=True, default="")
    asaas_status_commercial = models.CharField(max_length=32, blank=True, default="")
    asaas_status_documentation = models.CharField(max_length=32, blank=True, default="")
    asaas_status_bank = models.CharField(max_length=32, blank=True, default="")
    status_message = models.TextField(blank=True, default="")
    status_synced_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"AsaasSubaccount(tenant={self.tenant_id})"

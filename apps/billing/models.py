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


class SubscriptionCharge(models.Model):
    """
    Cobrança Asaas (pay_…) de uma assinatura SaaS, identificada de forma persistente.

    `overdue_at` marca a cobrança como exigida (vencida/recusada); só o pagamento
    confirmado desta cobrança (paid_at) a quita. A competência é o vencimento original.
    """

    subscription = models.ForeignKey(
        Subscription,
        on_delete=models.CASCADE,
        related_name="charges",
    )
    asaas_payment_id = models.CharField(max_length=64, unique=True)
    asaas_subscription_id = models.CharField(max_length=64, db_index=True)
    due_date = models.DateField(null=True, blank=True)
    original_due_date = models.DateField(null=True, blank=True)
    value = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    asaas_status = models.CharField(max_length=40, blank=True, default="")
    overdue_at = models.DateTimeField(null=True, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    removed_at = models.DateTimeField(null=True, blank=True)
    last_event = models.CharField(max_length=64, blank=True, default="")
    last_event_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["original_due_date", "due_date", "pk"]

    def __str__(self) -> str:
        return f"SubscriptionCharge({self.asaas_payment_id})"

    @property
    def competence(self):
        return self.original_due_date or self.due_date

    @property
    def is_outstanding(self) -> bool:
        return self.overdue_at is not None and self.paid_at is None and self.removed_at is None


class AsaasWebhookEvent(models.Model):
    """Registro de eventos Asaas de assinatura já processados (entrega at-least-once)."""

    event_key = models.CharField(max_length=191, unique=True)
    event = models.CharField(max_length=64)
    asaas_payment_id = models.CharField(max_length=64, blank=True, default="", db_index=True)
    asaas_subscription_id = models.CharField(max_length=64, blank=True, default="")
    event_created_at = models.DateTimeField(null=True, blank=True)
    outcome = models.CharField(max_length=64, blank=True, default="")
    received_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-received_at"]

    def __str__(self) -> str:
        return f"AsaasWebhookEvent({self.event} {self.event_key})"


class QaBillingSnapshot(models.Model):
    """Valores anteriores a uma alteração feita pelo qa_billing_delinquency (só QA/sandbox)."""

    tenant = models.ForeignKey(
        Tenant,
        on_delete=models.CASCADE,
        related_name="qa_billing_snapshots",
    )
    action = models.CharField(max_length=32)
    data = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    restored_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at", "-pk"]

    def __str__(self) -> str:
        return f"QaBillingSnapshot(tenant={self.tenant_id} {self.action})"


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

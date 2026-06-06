from decimal import Decimal

from django.db import models
from django.db.models import Q

from apps.financial.choices import PixKeyType
from apps.tenants.models import Tenant


class Wallet(models.Model):
    """Carteira virtual do mercado (tenant)."""

    tenant = models.OneToOneField(
        Tenant,
        on_delete=models.CASCADE,
        related_name="wallet",
    )
    balance_available = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0"),
    )
    balance_blocked = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0"),
    )
    default_pix_key = models.CharField(max_length=255, blank=True, default="")
    default_pix_key_type = models.CharField(
        max_length=16,
        choices=PixKeyType.choices,
        blank=True,
        default="",
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self) -> str:
        return f"Wallet(tenant={self.tenant_id}, available={self.balance_available})"

    @classmethod
    def get_or_create_for_tenant(cls, tenant_id: int) -> tuple["Wallet", bool]:
        return cls.objects.get_or_create(tenant_id=tenant_id)

    @property
    def has_default_pix_key(self) -> bool:
        return bool((self.default_pix_key or "").strip() and (self.default_pix_key_type or "").strip())


class LedgerTransaction(models.Model):
    """Movimentação no extrato da carteira."""

    class EntryType(models.TextChoices):
        INFLOW = "INFLOW", "Entrada"
        OUTFLOW = "OUTFLOW", "Saída"

    wallet = models.ForeignKey(
        Wallet,
        on_delete=models.CASCADE,
        related_name="transactions",
    )
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    entry_type = models.CharField(max_length=16, choices=EntryType.choices)
    description = models.CharField(max_length=255)
    external_id = models.CharField(max_length=64, blank=True, default="")
    cart = models.ForeignKey(
        "sales.Cart",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ledger_transactions",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["wallet", "-created_at"]),
            models.Index(fields=["external_id"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["external_id"],
                condition=Q(external_id__gt=""),
                name="uniq_ledger_asaas_payment",
            ),
        ]

    def __str__(self) -> str:
        return f"Ledger({self.entry_type}, {self.amount}, wallet={self.wallet_id})"


class WithdrawalRequest(models.Model):
    """Solicitação de saque via Pix."""

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pendente"
        PROCESSING = "PROCESSING", "Em processamento"
        PAID = "PAID", "Pago"
        REJECTED = "REJECTED", "Rejeitado"

    wallet = models.ForeignKey(
        Wallet,
        on_delete=models.CASCADE,
        related_name="withdrawals",
    )
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    pix_key = models.CharField(max_length=255)
    pix_key_type = models.CharField(max_length=16, choices=PixKeyType.choices)
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.PENDING,
    )
    asaas_transfer_id = models.CharField(max_length=64, blank=True, default="", db_index=True)
    ledger_transaction = models.OneToOneField(
        LedgerTransaction,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="withdrawal_request",
    )
    processed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["wallet", "status"]),
        ]

    def __str__(self) -> str:
        return f"Withdrawal(wallet={self.wallet_id}, {self.amount}, {self.status})"

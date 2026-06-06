from django.contrib import admin
from django.utils import timezone

from apps.financial.models import LedgerTransaction, Wallet, WithdrawalRequest


@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = (
        "tenant",
        "balance_available",
        "balance_blocked",
        "default_pix_key_type",
        "updated_at",
    )
    search_fields = ("tenant__name",)
    readonly_fields = ("updated_at",)


@admin.register(LedgerTransaction)
class LedgerTransactionAdmin(admin.ModelAdmin):
    list_display = (
        "wallet",
        "entry_type",
        "amount",
        "description",
        "external_id",
        "created_at",
    )
    list_filter = ("entry_type",)
    search_fields = ("description", "external_id")
    readonly_fields = ("created_at",)


@admin.register(WithdrawalRequest)
class WithdrawalRequestAdmin(admin.ModelAdmin):
    list_display = (
        "wallet",
        "amount",
        "pix_key_type",
        "status",
        "asaas_transfer_id",
        "created_at",
        "processed_at",
    )
    list_filter = ("status", "pix_key_type")
    search_fields = ("pix_key", "wallet__tenant__name")
    readonly_fields = ("created_at", "processed_at", "ledger_transaction")
    actions = ["mark_as_paid", "mark_as_rejected"]

    @admin.action(description="Marcar como pago")
    def mark_as_paid(self, request, queryset):
        from apps.financial.services.wallet import mark_withdrawal_paid

        for withdrawal in queryset.filter(status=WithdrawalRequest.Status.PENDING):
            mark_withdrawal_paid(withdrawal)

    @admin.action(description="Marcar como rejeitado (devolver saldo)")
    def mark_as_rejected(self, request, queryset):
        from apps.financial.services.wallet import mark_withdrawal_rejected

        for withdrawal in queryset.filter(status=WithdrawalRequest.Status.PENDING):
            mark_withdrawal_rejected(withdrawal)

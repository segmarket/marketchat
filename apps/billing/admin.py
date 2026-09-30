from django.contrib import admin

from apps.billing.models import (
    AsaasSubaccount,
    AsaasWebhookEvent,
    Subscription,
    SubscriptionCharge,
)


@admin.register(SubscriptionCharge)
class SubscriptionChargeAdmin(admin.ModelAdmin):
    list_display = (
        "asaas_payment_id",
        "subscription",
        "original_due_date",
        "due_date",
        "value",
        "asaas_status",
        "overdue_at",
        "paid_at",
        "removed_at",
        "last_event",
    )
    list_filter = ("asaas_status",)
    search_fields = ("asaas_payment_id", "asaas_subscription_id")
    readonly_fields = [f.name for f in SubscriptionCharge._meta.fields]


@admin.register(AsaasWebhookEvent)
class AsaasWebhookEventAdmin(admin.ModelAdmin):
    list_display = (
        "event_key",
        "event",
        "asaas_payment_id",
        "asaas_subscription_id",
        "outcome",
        "received_at",
        "processed_at",
    )
    list_filter = ("event", "outcome")
    search_fields = ("event_key", "asaas_payment_id", "asaas_subscription_id")
    readonly_fields = [f.name for f in AsaasWebhookEvent._meta.fields]


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = (
        "tenant",
        "status",
        "asaas_customer_id",
        "asaas_subscription_id",
        "trial_ends_at",
        "updated_at",
    )
    search_fields = ("asaas_customer_id", "asaas_subscription_id")


@admin.register(AsaasSubaccount)
class AsaasSubaccountAdmin(admin.ModelAdmin):
    list_display = (
        "tenant",
        "name",
        "email",
        "pix_key_type",
        "account_status",
        "asaas_wallet_id",
        "asaas_account_id",
        "asaas_status_general",
        "updated_at",
    )
    list_filter = ("account_status", "pix_key_type")
    search_fields = ("name", "email", "asaas_wallet_id", "cpf_cnpj")

from django.contrib import admin

from apps.billing.models import AsaasSubaccount, Subscription


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
        "updated_at",
    )
    list_filter = ("account_status", "pix_key_type")
    search_fields = ("name", "email", "asaas_wallet_id", "cpf_cnpj")

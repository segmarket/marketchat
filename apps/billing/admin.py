from django.contrib import admin

from apps.billing.models import Subscription


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

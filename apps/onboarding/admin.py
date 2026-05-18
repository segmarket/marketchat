from django.contrib import admin

from apps.onboarding.models import TenantOnboarding


@admin.register(TenantOnboarding)
class TenantOnboardingAdmin(admin.ModelAdmin):
    list_display = (
        "tenant",
        "step_market_created",
        "step_product_created",
        "step_whatsapp_connected",
        "step_test_order_completed",
        "onboarding_finished",
        "updated_at",
    )
    list_filter = ("onboarding_finished",)
    readonly_fields = ("created_at", "updated_at")

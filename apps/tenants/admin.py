from django.contrib import admin

from apps.tenants.models import DemoNote, Tenant


@admin.register(Tenant)
class TenantAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "slug",
        "subscription_status",
        "utm_source",
        "utm_campaign",
        "trial_ends_at",
        "billing_blocked_at",
        "whatsapp_logout_pending_since",
        "created_at",
    )
    list_filter = ("subscription_status",)
    search_fields = ("name", "slug", "utm_source", "utm_campaign", "gclid")
    readonly_fields = (
        "billing_suspension_notified_at",
        "whatsapp_logout_attempts",
        "whatsapp_logout_last_attempt_at",
        "whatsapp_logout_last_error",
        "utm_source",
        "utm_medium",
        "utm_campaign",
        "utm_term",
        "utm_content",
        "gclid",
        "fbclid",
        "created_at",
        "updated_at",
    )
    fieldsets = (
        (None, {"fields": ("name", "slug", "phone", "cpf_cnpj")}),
        (
            "Assinatura",
            {
                "fields": (
                    "trial_started_at",
                    "trial_ends_at",
                    "subscription_status",
                    "overdue_since",
                    "billing_blocked_at",
                    "billing_suspension_notified_at",
                )
            },
        ),
        (
            "Logout WhatsApp (suspensão)",
            {
                "fields": (
                    "whatsapp_logout_pending_since",
                    "whatsapp_logout_attempts",
                    "whatsapp_logout_last_attempt_at",
                    "whatsapp_logout_last_error",
                )
            },
        ),
        (
            "Marketing",
            {
                "fields": (
                    "utm_source",
                    "utm_medium",
                    "utm_campaign",
                    "utm_term",
                    "utm_content",
                    "gclid",
                    "fbclid",
                )
            },
        ),
        ("Metadados", {"fields": ("created_at", "updated_at")}),
    )


@admin.register(DemoNote)
class DemoNoteAdmin(admin.ModelAdmin):
    list_display = ("title", "tenant", "created_at")

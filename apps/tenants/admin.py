from django.contrib import admin

from apps.tenants.models import DemoNote, Tenant


@admin.register(Tenant)
class TenantAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "utm_source", "utm_campaign", "trial_ends_at", "billing_blocked_at", "created_at")
    search_fields = ("name", "slug", "utm_source", "utm_campaign", "gclid")
    readonly_fields = (
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

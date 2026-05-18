from django.contrib import admin

from apps.integrations.models import WhatsappInstance


@admin.register(WhatsappInstance)
class WhatsappInstanceAdmin(admin.ModelAdmin):
    list_display = (
        "instance_name",
        "tenant",
        "connection_status",
        "is_active",
        "updated_at",
    )
    list_filter = ("connection_status", "is_active")
    search_fields = ("instance_name", "instance_id", "tenant__name")
    readonly_fields = ("api_key", "webhook_secret", "created_at", "updated_at")

from django.contrib import admin

from apps.notifications.models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("id", "tenant", "title", "severity", "is_read", "created_at")
    list_filter = ("severity", "is_read")
    search_fields = ("title", "message")
    readonly_fields = ("created_at", "updated_at")

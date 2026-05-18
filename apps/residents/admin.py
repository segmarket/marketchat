from django.contrib import admin

from apps.residents.models import ChatSession, Resident


@admin.register(Resident)
class ResidentAdmin(admin.ModelAdmin):
    list_display = ("name", "phone_number", "tenant", "market", "created_at")
    list_filter = ("tenant",)
    search_fields = ("name", "phone_number")


@admin.register(ChatSession)
class ChatSessionAdmin(admin.ModelAdmin):
    list_display = ("phone_number", "tenant", "state", "temporary_name", "updated_at")
    list_filter = ("state", "tenant")

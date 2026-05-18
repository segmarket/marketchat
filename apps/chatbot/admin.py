from django.contrib import admin

from apps.chatbot.models import ChatbotWorkflow


@admin.register(ChatbotWorkflow)
class ChatbotWorkflowAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "tenant", "is_active", "updated_at")
    list_filter = ("is_active",)

from django.contrib import admin

from apps.chatbot.models import BotSchedule, ChatbotWorkflow


@admin.register(ChatbotWorkflow)
class ChatbotWorkflowAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "tenant", "is_active", "updated_at")
    list_filter = ("is_active",)


@admin.register(BotSchedule)
class BotScheduleAdmin(admin.ModelAdmin):
    list_display = ("id", "tenant", "day_of_week", "is_active", "start_time", "end_time")
    list_filter = ("is_active", "day_of_week")
    search_fields = ("tenant__name", "tenant__slug")

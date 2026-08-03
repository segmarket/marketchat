from django import forms
from django.contrib import admin
from django.db import models

from apps.chatbot.models import AIConfiguration, BotSchedule, ChatbotWorkflow


@admin.register(ChatbotWorkflow)
class ChatbotWorkflowAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "tenant", "is_active", "updated_at")
    list_filter = ("is_active",)


@admin.register(BotSchedule)
class BotScheduleAdmin(admin.ModelAdmin):
    list_display = ("id", "tenant", "day_of_week", "is_active", "start_time", "end_time")
    list_filter = ("is_active", "day_of_week")
    search_fields = ("tenant__name", "tenant__slug")


@admin.register(AIConfiguration)
class AIConfigurationAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "model_name",
        "temperature",
        "is_active",
        "updated_at",
    )
    list_filter = ("is_active",)
    search_fields = ("name", "model_name")
    readonly_fields = ("created_at", "updated_at")
    fields = (
        "name",
        "is_active",
        "model_name",
        "temperature",
        "system_prompt",
        "created_at",
        "updated_at",
    )
    formfield_overrides = {
        models.TextField: {
            "widget": forms.Textarea(attrs={"rows": 28, "cols": 100}),
        },
    }

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        if obj.is_active:
            AIConfiguration.objects.exclude(pk=obj.pk).filter(is_active=True).update(
                is_active=False,
            )

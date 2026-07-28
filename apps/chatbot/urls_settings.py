from django.urls import path

from apps.chatbot.views_bot_schedule import BotScheduleView

urlpatterns = [
    path("", BotScheduleView.as_view(), name="settings-bot-schedule"),
]

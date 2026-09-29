from django.urls import path

from apps.chatbot.views import (
    ChatbotWorkflowActiveView,
    ChatbotWorkflowDetailView,
    ChatbotWorkflowDuplicateView,
    ChatbotWorkflowListView,
    ChatbotWorkflowSaveView,
)
from apps.chatbot.views_analytics import ChatbotAnalyticsView
from apps.chatbot.views_chat_logs import (
    ChatLogsConversationView,
    ChatLogsListView,
    ChatMessageAttachmentView,
)
from apps.chatbot.views_handover import (
    ChatSessionAgentMessageView,
    ChatSessionToggleBotView,
)
from apps.chatbot.views_inbox import ChatSessionInboxListView

urlpatterns = [
    path("analytics/", ChatbotAnalyticsView.as_view(), name="chatbot-analytics"),
    path("logs/", ChatLogsListView.as_view(), name="chatbot-logs-list"),
    path(
        "logs/conversation/",
        ChatLogsConversationView.as_view(),
        name="chatbot-logs-conversation",
    ),
    path(
        "messages/<int:pk>/attachment/",
        ChatMessageAttachmentView.as_view(),
        name="chatbot-message-attachment",
    ),
    path(
        "sessions/",
        ChatSessionInboxListView.as_view(),
        name="chatbot-sessions-inbox",
    ),
    path(
        "sessions/<int:pk>/toggle-bot/",
        ChatSessionToggleBotView.as_view(),
        name="chatbot-session-toggle-bot",
    ),
    path(
        "sessions/<int:pk>/messages/",
        ChatSessionAgentMessageView.as_view(),
        name="chatbot-session-agent-message",
    ),
    path("workflows/", ChatbotWorkflowListView.as_view(), name="chatbot-workflows-list"),
    path(
        "workflows/active/",
        ChatbotWorkflowActiveView.as_view(),
        name="chatbot-workflows-active",
    ),
    path(
        "workflows/save/",
        ChatbotWorkflowSaveView.as_view(),
        name="chatbot-workflows-save",
    ),
    path(
        "workflows/<int:pk>/",
        ChatbotWorkflowDetailView.as_view(),
        name="chatbot-workflows-detail",
    ),
    path(
        "workflows/<int:pk>/duplicate/",
        ChatbotWorkflowDuplicateView.as_view(),
        name="chatbot-workflows-duplicate",
    ),
]

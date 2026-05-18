from django.urls import path

from apps.chatbot.views import (
    ChatbotWorkflowActiveView,
    ChatbotWorkflowDetailView,
    ChatbotWorkflowDuplicateView,
    ChatbotWorkflowListView,
    ChatbotWorkflowSaveView,
)

urlpatterns = [
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

from django.urls import path

from apps.support.views import (
    SupportChatView,
    SupportTicketCollectionView,
    SupportTicketDetailView,
    SupportTicketReplyView,
)

urlpatterns = [
    path("chat/", SupportChatView.as_view(), name="support-chat"),
    path("tickets/", SupportTicketCollectionView.as_view(), name="support-ticket-list"),
    path("tickets/<int:pk>/", SupportTicketDetailView.as_view(), name="support-ticket-detail"),
    path("tickets/<int:pk>/reply/", SupportTicketReplyView.as_view(), name="support-ticket-reply"),
]

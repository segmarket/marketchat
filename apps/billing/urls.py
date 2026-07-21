from django.urls import path

from apps.billing.views import AsaasWebhookView
from apps.billing.views_chat_pix import GenerateChatPixView

urlpatterns = [
    path("webhooks/asaas/", AsaasWebhookView.as_view(), name="asaas-webhook"),
]

payments_urlpatterns = [
    path(
        "generate-pix-chat/",
        GenerateChatPixView.as_view(),
        name="payments-generate-pix-chat",
    ),
]

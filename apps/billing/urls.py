from django.urls import path

from apps.billing.views import AsaasWebhookView

urlpatterns = [
    path("webhooks/asaas/", AsaasWebhookView.as_view(), name="asaas-webhook"),
]

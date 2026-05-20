from django.urls import path

from apps.integrations.views_webhook import EvolutionWebhookView

urlpatterns = [
    path("evolution", EvolutionWebhookView.as_view(), name="webhook-evolution-no-slash"),
    path("evolution/", EvolutionWebhookView.as_view(), name="webhook-evolution"),
]

from django.urls import include, path

from apps.integrations.views import (
    WhatsappDisconnectView,
    WhatsappInstanceView,
    WhatsappProvisionView,
    WhatsappQrcodeView,
    WhatsappRestartView,
    WhatsappStatusView,
)
from apps.integrations.views_avatar import WhatsappAvatarRefreshView
from apps.integrations.views_pix import PixIntegrationView

urlpatterns = [
    path("pix/", PixIntegrationView.as_view(), name="integrations-pix"),
    path("webhooks/", include("apps.integrations.urls_webhooks")),
    path("whatsapp/", WhatsappInstanceView.as_view(), name="integrations-whatsapp"),
    path(
        "whatsapp/provision/",
        WhatsappProvisionView.as_view(),
        name="integrations-whatsapp-provision",
    ),
    path(
        "whatsapp/qrcode/",
        WhatsappQrcodeView.as_view(),
        name="integrations-whatsapp-qrcode",
    ),
    path(
        "whatsapp/status/",
        WhatsappStatusView.as_view(),
        name="integrations-whatsapp-status",
    ),
    path(
        "whatsapp/disconnect/",
        WhatsappDisconnectView.as_view(),
        name="integrations-whatsapp-disconnect",
    ),
    path(
        "whatsapp/restart/",
        WhatsappRestartView.as_view(),
        name="integrations-whatsapp-restart",
    ),
    path(
        "whatsapp/avatar/refresh/",
        WhatsappAvatarRefreshView.as_view(),
        name="integrations-whatsapp-avatar-refresh",
    ),
]

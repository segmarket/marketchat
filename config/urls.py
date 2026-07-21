from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from apps.billing.views import AsaasWebhookView
from apps.billing.urls import payments_urlpatterns
from apps.financial.views_webhooks import AsaasWithdrawalValidationWebhookView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/auth/", include("apps.accounts.urls")),
    path("api/settings/account/", include("apps.accounts.urls_settings")),
    path("api/settings/billing/", include("apps.billing.urls_settings")),
    path("api/billing/", include("apps.billing.urls")),
    path("api/payments/", include(payments_urlpatterns)),
    path("api/webhooks/asaas/", AsaasWebhookView.as_view(), name="asaas-webhook-public"),

    path(
        "api/webhooks/asaas/validate-transfer/",
        AsaasWithdrawalValidationWebhookView.as_view(),
        name="asaas-withdrawal-validation",
    ),
    path("api/integrations/", include("apps.integrations.urls")),
    path("api/products/", include("apps.products.urls")),
    path("api/markets/", include("apps.markets.urls")),
    path("api/residents/", include("apps.residents.urls")),
    path("api/chatbot/", include("apps.chatbot.urls")),
    path("api/sales/", include("apps.sales.urls")),
    path("api/financial/", include("apps.financial.urls")),
    path("api/notifications/", include("apps.notifications.urls")),
    path("api/onboarding/", include("apps.onboarding.urls")),
    path("api/support/", include("apps.support.urls")),
    path("api/lgpd/", include("apps.lgpd.urls")),
    path("api/", include("apps.tenants.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

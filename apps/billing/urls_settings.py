from django.urls import path

from apps.billing.views_settings import BillingHistoryView, PaymentMethodView

urlpatterns = [
    path("history/", BillingHistoryView.as_view(), name="settings-billing-history"),
    path(
        "payment-method/",
        PaymentMethodView.as_view(),
        name="settings-billing-payment-method",
    ),
]

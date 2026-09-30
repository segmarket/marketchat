from django.urls import path

from apps.billing.views_settings import (
    BillingHistoryView,
    CancelSubscriptionView,
    PaymentMethodView,
    ReactivateSubscriptionView,
    RegularizeView,
)

urlpatterns = [
    path("history/", BillingHistoryView.as_view(), name="settings-billing-history"),
    path(
        "payment-method/",
        PaymentMethodView.as_view(),
        name="settings-billing-payment-method",
    ),
    path(
        "regularize/",
        RegularizeView.as_view(),
        name="settings-billing-regularize",
    ),
    path(
        "subscription/cancel/",
        CancelSubscriptionView.as_view(),
        name="settings-billing-cancel-subscription",
    ),
    path(
        "subscription/reactivate/",
        ReactivateSubscriptionView.as_view(),
        name="settings-billing-reactivate-subscription",
    ),
]

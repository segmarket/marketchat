from django.urls import path

from apps.sales.views_dashboard import SalesCartDetailView, SalesDashboardView

urlpatterns = [
    path("dashboard/", SalesDashboardView.as_view(), name="sales-dashboard"),
    path(
        "carts/<int:pk>/",
        SalesCartDetailView.as_view(),
        name="sales-cart-detail",
    ),
]

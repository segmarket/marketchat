from django.urls import path

from apps.residents.views import (
    ResidentDetailView,
    ResidentListView,
    ResidentMarketListView,
)

urlpatterns = [
    path("", ResidentListView.as_view(), name="residents-list"),
    path("markets/", ResidentMarketListView.as_view(), name="residents-markets"),
    path("<int:pk>/", ResidentDetailView.as_view(), name="residents-detail"),
]

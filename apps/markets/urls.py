from django.urls import path

from apps.markets.views import MarketDetailView, MarketListCreateView

urlpatterns = [
    path("", MarketListCreateView.as_view(), name="markets-list"),
    path("<int:pk>/", MarketDetailView.as_view(), name="markets-detail"),
]

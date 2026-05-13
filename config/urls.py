from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/auth/", include("apps.accounts.urls")),
    path("api/billing/", include("apps.billing.urls")),
    path("api/", include("apps.tenants.urls")),
]

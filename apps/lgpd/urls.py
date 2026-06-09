from django.urls import path

from apps.lgpd.views import (
    LgpdResidentAnonymizeView,
    LgpdResidentExportView,
    LgpdTenantExportView,
)

urlpatterns = [
    path("export/", LgpdTenantExportView.as_view(), name="lgpd-tenant-export"),
    path(
        "residents/<int:pk>/export/",
        LgpdResidentExportView.as_view(),
        name="lgpd-resident-export",
    ),
    path(
        "residents/anonymize/",
        LgpdResidentAnonymizeView.as_view(),
        name="lgpd-resident-anonymize",
    ),
]

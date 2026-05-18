from django.urls import path

from apps.accounts.views_settings import AccountSettingsView

urlpatterns = [
    path("", AccountSettingsView.as_view(), name="settings-account"),
]

from django.urls import path

from apps.financial.views import (
    FinancialStatementView,
    FinancialWalletSettingsView,
    FinancialWithdrawView,
)

urlpatterns = [
    path("statement/", FinancialStatementView.as_view(), name="financial-statement"),
    path("wallet/settings/", FinancialWalletSettingsView.as_view(), name="financial-wallet-settings"),
    path("withdraw/", FinancialWithdrawView.as_view(), name="financial-withdraw"),
]

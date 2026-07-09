from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from apps.accounts.views import (
    ChangePasswordView,
    MeView,
    PasswordResetConfirmView,
    PasswordResetRequestView,
    RegisterView,
    SignupLeadView,
    TenantTokenObtainPairView,
)

urlpatterns = [
    path("me/", MeView.as_view(), name="auth-me"),
    path("signup-lead/", SignupLeadView.as_view(), name="auth-signup-lead"),
    path("register/", RegisterView.as_view(), name="auth-register"),
    path("token/", TenantTokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("password/change/", ChangePasswordView.as_view(), name="password-change"),
    path("password/reset/", PasswordResetRequestView.as_view(), name="password-reset"),
    path("password/reset/confirm/", PasswordResetConfirmView.as_view(), name="password-reset-confirm"),
]

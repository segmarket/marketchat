from __future__ import annotations

import logging

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView

from apps.accounts.serializers import (
    ChangePasswordSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    RegisterSerializer,
    TenantTokenObtainPairSerializer,
)
from apps.core.emails import send_password_reset_email_safe
from apps.tenants.models import Tenant

User = get_user_model()
logger = logging.getLogger(__name__)


class TenantTokenObtainPairView(TokenObtainPairView):
    serializer_class = TenantTokenObtainPairSerializer


class MeView(APIView):
    """Perfil do usuário autenticado e dados do tenant (acessível mesmo com billing suspenso)."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        tenant_payload = None
        billing_blocked = False
        subscription_status = Tenant.SubscriptionStatus.TRIAL
        days_left_in_trial = 0
        trial_expired = False
        subscription_canceled = False
        is_in_grace_period = False
        days_overdue = 0
        if user.tenant_id:
            tenant = Tenant.objects.filter(pk=user.tenant_id).first()
            if tenant:
                tenant_payload = {
                    "id": tenant.id,
                    "name": tenant.name,
                    "slug": tenant.slug,
                }
                billing_blocked = tenant.billing_blocked_at is not None
                subscription_status = tenant.subscription_status
                days_left_in_trial = tenant.days_left_in_trial()
                is_in_grace_period = tenant.is_in_grace_period()
                days_overdue = tenant.days_overdue()
                trial_expired = (
                    not tenant.has_panel_access() and tenant.is_trial_period_over()
                )
                subscription_canceled = (
                    subscription_status == Tenant.SubscriptionStatus.CANCELED
                )
        return Response(
            {
                "id": user.id,
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "tenant": tenant_payload,
                "billing_blocked": billing_blocked,
                "subscription_status": subscription_status,
                "days_left_in_trial": days_left_in_trial,
                "trial_expired": trial_expired,
                "subscription_canceled": subscription_canceled,
                "is_in_grace_period": is_in_grace_period,
                "days_overdue": days_overdue,
            }
        )


class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        logger.info(
            "POST /api/auth/register/ recebido (email=%s, empresa=%s)",
            request.data.get("admin_email"),
            request.data.get("company_name"),
        )
        serializer = RegisterSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(
            {
                "id": user.id,
                "email": user.email,
                "tenant_id": user.tenant_id,
            },
            status=status.HTTP_201_CREATED,
        )


class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        if not request.user.check_password(serializer.validated_data["old_password"]):
            return Response({"old_password": ["Senha atual incorreta."]}, status=status.HTTP_400_BAD_REQUEST)
        request.user.set_password(serializer.validated_data["new_password"])
        request.user.save(update_fields=["password"])
        return Response(status=status.HTTP_204_NO_CONTENT)


class PasswordResetRequestView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"]
        user = User.objects.filter(email__iexact=email).first()
        if user:
            send_password_reset_email_safe(user)
        return Response(
            {"detail": "Se o e-mail existir em nossa base, você receberá instruções em instantes."},
            status=status.HTTP_200_OK,
        )


class PasswordResetConfirmView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"detail": "Senha atualizada com sucesso."}, status=status.HTTP_200_OK)

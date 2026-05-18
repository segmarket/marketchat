from __future__ import annotations

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.serializers_settings import (
    AccountSettingsUpdateSerializer,
    build_account_settings_payload,
)
from apps.tenants.models import Tenant


class AccountSettingsView(APIView):
    """Perfil do usuário e dados da empresa (tenant do JWT)."""

    permission_classes = [IsAuthenticated]

    def _get_tenant(self, request) -> Tenant | None:
        tid = getattr(request.user, "tenant_id", None)
        if not tid:
            return None
        return Tenant.objects.filter(pk=tid).first()

    def get(self, request):
        tenant = self._get_tenant(request)
        if request.user.tenant_id and tenant is None:
            return Response({"detail": "Tenant inválido."}, status=status.HTTP_403_FORBIDDEN)
        return Response(build_account_settings_payload(request.user, tenant))

    def patch(self, request):
        tenant = self._get_tenant(request)
        if request.user.tenant_id and tenant is None:
            return Response({"detail": "Tenant inválido."}, status=status.HTTP_403_FORBIDDEN)

        serializer = AccountSettingsUpdateSerializer(
            data=request.data,
            partial=True,
            context={"user": request.user, "tenant": tenant},
        )
        serializer.is_valid(raise_exception=True)
        user, tenant = serializer.save()
        return Response(build_account_settings_payload(user, tenant))

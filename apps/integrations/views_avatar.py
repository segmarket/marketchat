"""Atualização assíncrona-friendly do avatar (não bloqueia o GET principal)."""

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import IsTenantAdmin
from apps.integrations.models import WhatsappInstance
from apps.integrations.services.instance_dashboard import build_dashboard_payload
from apps.integrations.services.profile_sync import sync_profile_avatar_from_evolution
from apps.integrations.views import _get_active_instance


class WhatsappAvatarRefreshView(APIView):
    permission_classes = [IsAuthenticated, IsTenantAdmin]

    def post(self, request: Request) -> Response:
        instance = _get_active_instance(request)
        if not instance:
            return Response({"detail": "Nenhuma instância WhatsApp ativa."}, status=404)
        if instance.connection_status != WhatsappInstance.ConnectionStatus.OPEN:
            return Response(
                {"detail": "WhatsApp precisa estar conectado para buscar a foto."},
                status=status.HTTP_409_CONFLICT,
            )
        sync_profile_avatar_from_evolution(instance, try_both_previews=True)
        instance.refresh_from_db()
        return Response(
            build_dashboard_payload(
                instance,
                request_user=request.user,
                sync_evolution=False,
            )
        )

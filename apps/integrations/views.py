from django.db import IntegrityError
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import IsTenantAdmin
from apps.integrations.models import WhatsappInstance
from apps.integrations.serializers import WhatsappProvisionSerializer
from apps.integrations.services.instance_dashboard import build_dashboard_payload
from apps.integrations.services.provisioning import (
    EvolutionProvisionError,
    WhatsappAlreadyProvisionedError,
    disconnect_whatsapp_instance,
    provision_whatsapp_instance,
    reconcile_whatsapp_with_evolution,
    refresh_qrcode,
    sync_connection_status,
)
from apps.integrations.services.restart import EvolutionRestartError, restart_whatsapp_instance


def _get_active_instance(request: Request) -> WhatsappInstance | None:
    return (
        WhatsappInstance.objects.filter(
            tenant_id=request.user.tenant_id,
            is_active=True,
        )
        .order_by("-id")
        .first()
    )


def _get_reconciled_active_instance(request: Request) -> WhatsappInstance | None:
    instance = _get_active_instance(request)
    if not instance:
        return None
    return reconcile_whatsapp_with_evolution(instance)


class WhatsappInstanceView(APIView):
    """Estado da integração: leitura para qualquer membro autenticado do tenant."""

    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        instance = _get_reconciled_active_instance(request)
        return Response(
            build_dashboard_payload(
                instance,
                request_user=request.user,
                sync_evolution=bool(instance and instance.is_active),
            )
        )


class WhatsappProvisionView(APIView):
    permission_classes = [IsAuthenticated, IsTenantAdmin]

    def post(self, request: Request) -> Response:
        ser = WhatsappProvisionSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        pair_phone = ser.validated_data.get("pair_phone", "")
        try:
            result = provision_whatsapp_instance(
                request.user.tenant,
                pair_phone=pair_phone,
            )
        except WhatsappAlreadyProvisionedError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)
        except IntegrityError:
            return Response(
                {
                    "detail": (
                        "Já existe um registro de WhatsApp para esta empresa. "
                        "Use Desconectar e tente novamente, ou contate o suporte."
                    ),
                },
                status=status.HTTP_409_CONFLICT,
            )
        except EvolutionProvisionError as exc:
            return Response(
                {"detail": str(exc), "step": exc.step},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        instance = result["instance"]
        data = build_dashboard_payload(
            instance,
            request_user=request.user,
            qrcode_image=result.get("qrcode_image", ""),
            sync_evolution=True,
            refresh_avatar=True,
        )
        return Response(data, status=status.HTTP_201_CREATED)


class WhatsappQrcodeView(APIView):
    permission_classes = [IsAuthenticated, IsTenantAdmin]

    def get(self, request: Request) -> Response:
        instance = _get_active_instance(request)
        if not instance:
            return Response({"detail": "Nenhuma instância WhatsApp ativa."}, status=404)
        try:
            result = refresh_qrcode(instance)
        except Exception as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)

        data = build_dashboard_payload(
            instance,
            request_user=request.user,
            qrcode_image=result.get("qrcode_image", ""),
            sync_evolution=True,
        )
        return Response(data)


class WhatsappStatusView(APIView):
    permission_classes = [IsAuthenticated, IsTenantAdmin]

    def get(self, request: Request) -> Response:
        instance = _get_reconciled_active_instance(request)
        if not instance:
            return Response(build_dashboard_payload(None, request_user=request.user))
        try:
            sync_connection_status(instance)
        except EvolutionProvisionError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)
        instance.refresh_from_db()
        if not instance.is_active:
            return Response(build_dashboard_payload(None, request_user=request.user))

        return Response(
            build_dashboard_payload(
                instance,
                request_user=request.user,
                sync_evolution=True,
            )
        )


class WhatsappRestartView(APIView):
    permission_classes = [IsAuthenticated, IsTenantAdmin]

    def post(self, request: Request) -> Response:
        instance = _get_active_instance(request)
        if not instance:
            return Response({"detail": "Nenhuma instância WhatsApp ativa."}, status=404)
        try:
            restart_whatsapp_instance(instance)
        except EvolutionRestartError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)

        return Response(
            build_dashboard_payload(
                instance,
                request_user=request.user,
                sync_evolution=True,
                refresh_avatar=True,
            )
        )


class WhatsappDisconnectView(APIView):
    permission_classes = [IsAuthenticated, IsTenantAdmin]

    def post(self, request: Request) -> Response:
        instance = _get_active_instance(request)
        if not instance:
            return Response({"detail": "Nenhuma instância WhatsApp ativa."}, status=404)
        disconnect_whatsapp_instance(instance)
        instance.refresh_from_db()
        return Response(build_dashboard_payload(instance, request_user=request.user))

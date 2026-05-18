from __future__ import annotations

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.notifications.models import Notification
from apps.notifications.serializers import NotificationSerializer
from apps.tenants.context import tenant_scope


def _tenant_id_from_request(request: Request) -> int | None:
    tenant_id = getattr(request.user, "tenant_id", None)
    if tenant_id is None:
        return None
    return int(tenant_id)


class NotificationsLatestView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        tenant_id = _tenant_id_from_request(request)
        if not tenant_id:
            return Response(
                {"detail": "Conta sem empresa vinculada."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        with tenant_scope(tenant_id):
            unread_qs = (
                Notification.objects.filter(is_read=False)
                .select_related("market")
                .order_by("-created_at")
            )
            unread_count = unread_qs.count()
            latest = unread_qs[:5]
            serializer = NotificationSerializer(latest, many=True)

        return Response(
            {
                "unread_count": unread_count,
                "results": serializer.data,
            }
        )


class NotificationReadView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request: Request, pk: int) -> Response:
        tenant_id = _tenant_id_from_request(request)
        if not tenant_id:
            return Response(
                {"detail": "Conta sem empresa vinculada."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        with tenant_scope(tenant_id):
            try:
                notification = Notification.objects.get(pk=pk)
            except Notification.DoesNotExist:
                return Response(status=status.HTTP_404_NOT_FOUND)

            if not notification.is_read:
                notification.is_read = True
                notification.save(update_fields=["is_read", "updated_at"])

            serializer = NotificationSerializer(notification)

        return Response(serializer.data)


class NotificationsReadAllView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request: Request) -> Response:
        tenant_id = _tenant_id_from_request(request)
        if not tenant_id:
            return Response(
                {"detail": "Conta sem empresa vinculada."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        with tenant_scope(tenant_id):
            updated = Notification.objects.filter(is_read=False).update(is_read=True)

        return Response({"marked_read": updated})

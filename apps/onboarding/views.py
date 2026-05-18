from __future__ import annotations

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.onboarding.serializers import OnboardingStatusSerializer
from apps.onboarding.services import (
    build_status_payload,
    dismiss_onboarding,
    sync_tenant_onboarding,
)


def _tenant_id_from_request(request: Request) -> int | None:
    tenant_id = getattr(request.user, "tenant_id", None)
    if tenant_id is None:
        return None
    return int(tenant_id)


class OnboardingStatusView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        tenant_id = _tenant_id_from_request(request)
        if not tenant_id:
            return Response(
                {"detail": "Conta sem empresa vinculada."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        record = sync_tenant_onboarding(tenant_id)
        payload = build_status_payload(record)
        serializer = OnboardingStatusSerializer(payload)
        return Response(serializer.data)


class OnboardingDismissView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request: Request) -> Response:
        tenant_id = _tenant_id_from_request(request)
        if not tenant_id:
            return Response(
                {"detail": "Conta sem empresa vinculada."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            record = dismiss_onboarding(tenant_id)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        payload = build_status_payload(record)
        serializer = OnboardingStatusSerializer(payload)
        return Response(serializer.data)

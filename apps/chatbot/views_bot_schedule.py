from __future__ import annotations

from datetime import time

from django.db import transaction
from rest_framework import serializers, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.chatbot.models import BotSchedule
from apps.chatbot.services.bot_schedule import list_bot_schedule
from apps.tenants.models import Tenant


class BotScheduleDaySerializer(serializers.Serializer):
    day_of_week = serializers.IntegerField(min_value=0, max_value=6)
    is_active = serializers.BooleanField()
    start_time = serializers.TimeField()
    end_time = serializers.TimeField()

    def validate(self, attrs):
        if attrs.get("is_active") and attrs["start_time"] >= attrs["end_time"]:
            raise serializers.ValidationError(
                {"end_time": "Hora de término deve ser posterior à de início."},
            )
        return attrs


class BotSchedulePutSerializer(serializers.Serializer):
    days = BotScheduleDaySerializer(many=True)

    def validate_days(self, value):
        if len(value) != 7:
            raise serializers.ValidationError("Informe exatamente 7 dias (0 a 6).")
        days = [item["day_of_week"] for item in value]
        if sorted(days) != list(range(7)):
            raise serializers.ValidationError(
                "Cada day_of_week de 0 a 6 deve aparecer uma vez.",
            )
        return value


class BotGlobalActiveSerializer(serializers.Serializer):
    is_bot_active_global = serializers.BooleanField()


def _tenant_or_403(request) -> Tenant | Response:
    tid = getattr(request.user, "tenant_id", None)
    if not tid:
        return Response({"detail": "Tenant inválido."}, status=status.HTTP_403_FORBIDDEN)
    tenant = Tenant.objects.filter(pk=tid).first()
    if tenant is None:
        return Response({"detail": "Tenant inválido."}, status=status.HTTP_403_FORBIDDEN)
    return tenant


def _schedule_payload(tenant: Tenant) -> dict:
    return {
        "is_bot_active_global": tenant.is_bot_active_global,
        "days": list_bot_schedule(tenant.pk),
    }


class BotScheduleView(APIView):
    """GET/PUT grade de horário + PATCH chave geral do bot."""

    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        tenant = _tenant_or_403(request)
        if isinstance(tenant, Response):
            return tenant
        return Response(_schedule_payload(tenant))

    def put(self, request: Request) -> Response:
        tenant = _tenant_or_403(request)
        if isinstance(tenant, Response):
            return tenant

        serializer = BotSchedulePutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        days = serializer.validated_data["days"]

        with transaction.atomic():
            for item in days:
                start: time = item["start_time"]
                end: time = item["end_time"]
                BotSchedule.objects.update_or_create(
                    tenant_id=tenant.pk,
                    day_of_week=item["day_of_week"],
                    defaults={
                        "is_active": item["is_active"],
                        "start_time": start,
                        "end_time": end,
                    },
                )

        tenant.refresh_from_db(fields=["is_bot_active_global"])
        return Response(_schedule_payload(tenant))

    def patch(self, request: Request) -> Response:
        tenant = _tenant_or_403(request)
        if isinstance(tenant, Response):
            return tenant

        serializer = BotGlobalActiveSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        tenant.is_bot_active_global = serializer.validated_data["is_bot_active_global"]
        tenant.save(update_fields=["is_bot_active_global", "updated_at"])
        return Response(_schedule_payload(tenant))

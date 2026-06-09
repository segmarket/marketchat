from __future__ import annotations

import json

from django.http import HttpResponse
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import IsTenantAdmin
from apps.lgpd.services.anonymization import (
    ResidentAnonymizationError,
    anonymize_resident_by_phone,
)
from apps.lgpd.services.export import build_resident_export_json, build_tenant_export_json
from apps.residents.models import Resident
from apps.tenants.models import Tenant


class LgpdTenantExportView(APIView):
    permission_classes = [IsAuthenticated, IsTenantAdmin]

    def get(self, request: Request) -> HttpResponse:
        tenant_id = getattr(request.user, "tenant_id", None)
        if not tenant_id:
            return Response({"detail": "Conta sem empresa vinculada."}, status=400)

        tenant = Tenant.objects.get(pk=tenant_id)
        payload = build_tenant_export_json(tenant=tenant, user=request.user)
        body = json.dumps(payload, ensure_ascii=False, indent=2)
        response = HttpResponse(body, content_type="application/json; charset=utf-8")
        response["Content-Disposition"] = (
            'attachment; filename="marketchat-lgpd-export.json"'
        )
        return response


class LgpdResidentExportView(APIView):
    permission_classes = [IsAuthenticated, IsTenantAdmin]

    def get(self, request: Request, pk: int) -> HttpResponse:
        tenant_id = getattr(request.user, "tenant_id", None)
        if not tenant_id:
            return Response({"detail": "Conta sem empresa vinculada."}, status=400)

        try:
            resident = Resident.objects.select_related("market").get(
                pk=pk,
                tenant_id=tenant_id,
            )
        except Resident.DoesNotExist:
            return Response({"detail": "Morador não encontrado."}, status=404)

        payload = build_resident_export_json(resident=resident)
        body = json.dumps(payload, ensure_ascii=False, indent=2)
        response = HttpResponse(body, content_type="application/json; charset=utf-8")
        response["Content-Disposition"] = (
            f'attachment; filename="marketchat-morador-{resident.id}-lgpd.json"'
        )
        return response


class LgpdResidentAnonymizeView(APIView):
    permission_classes = [IsAuthenticated, IsTenantAdmin]

    def post(self, request: Request) -> Response:
        tenant_id = getattr(request.user, "tenant_id", None)
        if not tenant_id:
            return Response({"detail": "Conta sem empresa vinculada."}, status=400)

        phone = (request.data.get("phone") or "").strip()
        if not phone:
            return Response({"detail": "Informe o telefone do morador."}, status=400)

        try:
            resident = anonymize_resident_by_phone(tenant_id=tenant_id, phone=phone)
        except ResidentAnonymizationError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(
            {
                "resident_id": resident.id,
                "is_anonymized": resident.is_anonymized,
                "message": "Dados do morador anonimizados com sucesso. Histórico financeiro preservado.",
            },
            status=status.HTTP_200_OK,
        )

from __future__ import annotations

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import IsTenantAdmin
from apps.accounts.services.tenant_access import user_can_manage_tenant
from apps.billing.models import AsaasSubaccount
from apps.billing.services.asaas_subaccount import (
    SubaccountSetupError,
    create_tenant_subaccount,
    get_primary_market_address,
    market_address_is_valid,
)
from apps.integrations.serializers_pix import PixConfigWriteSerializer
from apps.tenants.models import Tenant


def _get_tenant(request: Request) -> Tenant | None:
    tid = getattr(request.user, "tenant_id", None)
    if not tid:
        return None
    return Tenant.objects.filter(pk=tid).first()


def _build_prefill(tenant: Tenant | None, user) -> dict:
    if tenant is None:
        return {"name": "", "email": getattr(user, "email", "") or "", "cpf_cnpj": ""}
    return {
        "name": tenant.name or "",
        "email": getattr(user, "email", "") or "",
        "cpf_cnpj": (tenant.cpf_cnpj or "").strip(),
    }


def _build_pix_payload(
    subaccount: AsaasSubaccount | None,
    tenant: Tenant | None,
    user,
) -> dict:
    prefill = _build_prefill(tenant, user)
    market_parts = get_primary_market_address(tenant.id) if tenant else None
    has_market_address = market_address_is_valid(market_parts) if market_parts else False

    if subaccount is None:
        return {
            "name": prefill["name"],
            "email": prefill["email"],
            "cpf_cnpj": prefill["cpf_cnpj"],
            "pix_key_type": AsaasSubaccount.PixKeyType.CPF,
            "pix_key": "",
            "asaas_wallet_id": "",
            "account_status": AsaasSubaccount.AccountStatus.PENDING,
            "has_wallet": False,
            "prefill": prefill,
            "has_market_address": has_market_address,
            "can_manage": user_can_manage_tenant(user),
        }

    return {
        "name": subaccount.name,
        "email": subaccount.email,
        "cpf_cnpj": subaccount.cpf_cnpj,
        "pix_key_type": subaccount.pix_key_type,
        "pix_key": subaccount.pix_key,
        "asaas_wallet_id": subaccount.asaas_wallet_id or "",
        "account_status": subaccount.account_status,
        "has_wallet": bool(subaccount.asaas_wallet_id),
        "prefill": prefill,
        "has_market_address": has_market_address,
        "can_manage": user_can_manage_tenant(user),
    }


class PixIntegrationView(APIView):
    def get_permissions(self):
        if self.request.method == "PUT":
            return [IsAuthenticated(), IsTenantAdmin()]
        return [IsAuthenticated()]

    def get(self, request: Request) -> Response:
        tenant = _get_tenant(request)
        if request.user.tenant_id and tenant is None:
            return Response({"detail": "Tenant inválido."}, status=status.HTTP_403_FORBIDDEN)

        subaccount = None
        if tenant is not None:
            subaccount = AsaasSubaccount.objects.filter(tenant=tenant).first()

        return Response(_build_pix_payload(subaccount, tenant, request.user))

    def put(self, request: Request) -> Response:
        tenant = _get_tenant(request)
        if tenant is None:
            return Response({"detail": "Tenant inválido."}, status=status.HTTP_403_FORBIDDEN)

        ser = PixConfigWriteSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data

        subaccount, _created = AsaasSubaccount.objects.update_or_create(
            tenant=tenant,
            defaults={
                "name": data["name"],
                "email": data["email"],
                "cpf_cnpj": data["cpf_cnpj"],
                "pix_key_type": data["pix_key_type"],
                "pix_key": data["pix_key"],
            },
        )

        if not subaccount.asaas_wallet_id:
            try:
                subaccount = create_tenant_subaccount(subaccount)
            except SubaccountSetupError as exc:
                return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        else:
            subaccount.save(
                update_fields=[
                    "name",
                    "email",
                    "cpf_cnpj",
                    "pix_key_type",
                    "pix_key",
                    "updated_at",
                ],
            )

        return Response(_build_pix_payload(subaccount, tenant, request.user))

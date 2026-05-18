from __future__ import annotations

import logging

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import IsTenantAdmin
from apps.billing.serializers_settings import UpdatePaymentMethodSerializer
from apps.billing.services.asaas_client import AsaasAPIError
from apps.billing.services.billing_history import get_billing_history_for_tenant
from apps.billing.services.payment_method import (
    get_payment_method_summary,
    update_subscription_card,
)
from apps.tenants.models import Tenant

logger = logging.getLogger(__name__)


class BillingSettingsBaseView(APIView):
    permission_classes = [IsAuthenticated, IsTenantAdmin]

    def _get_tenant(self, request) -> Tenant | None:
        tid = getattr(request.user, "tenant_id", None)
        if not tid:
            return None
        return Tenant.objects.filter(pk=tid).first()

    def _tenant_or_error(self, request) -> Tenant | Response:
        tenant = self._get_tenant(request)
        if request.user.tenant_id and tenant is None:
            return Response({"detail": "Tenant inválido."}, status=status.HTTP_403_FORBIDDEN)
        if tenant is None:
            return Response(
                {"detail": "Usuário sem empresa vinculada."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return tenant


class BillingHistoryView(BillingSettingsBaseView):
    def get(self, request):
        tenant = self._tenant_or_error(request)
        if isinstance(tenant, Response):
            return tenant
        try:
            history = get_billing_history_for_tenant(tenant)
        except AsaasAPIError as exc:
            logger.warning("Asaas billing history: %s", exc.payload or exc)
            return Response(
                {"detail": "Não foi possível consultar o histórico de cobranças."},
                status=status.HTTP_502_BAD_GATEWAY,
            )
        return Response({"results": history})


class PaymentMethodView(BillingSettingsBaseView):
    def get(self, request):
        tenant = self._tenant_or_error(request)
        if isinstance(tenant, Response):
            return tenant
        try:
            summary = get_payment_method_summary(tenant)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_404_NOT_FOUND)
        except AsaasAPIError as exc:
            logger.warning("Asaas payment method: %s", exc.payload or exc)
            return Response(
                {"detail": "Não foi possível consultar a forma de pagamento."},
                status=status.HTTP_502_BAD_GATEWAY,
            )
        return Response(summary)

    def post(self, request):
        tenant = self._tenant_or_error(request)
        if isinstance(tenant, Response):
            return tenant

        serializer = UpdatePaymentMethodSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        card = serializer.validated_data["credit_card"]
        holder = dict(serializer.validated_data["credit_card_holder"])
        if not (holder.get("cpfCnpj") or "").strip():
            holder.pop("cpfCnpj", None)

        forwarded = (request.META.get("HTTP_X_FORWARDED_FOR") or "").split(",")[0].strip()
        remote_ip = forwarded or request.META.get("REMOTE_ADDR") or ""

        try:
            summary = update_subscription_card(
                tenant,
                dict(card),
                holder,
                remote_ip,
            )
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_404_NOT_FOUND)
        except AsaasAPIError as exc:
            logger.warning("Asaas update card: %s", exc.payload or exc)
            detail = "Não foi possível atualizar o cartão."
            if exc.payload and isinstance(exc.payload, dict):
                errors = exc.payload.get("errors")
                if errors:
                    detail = str(errors[0].get("description", detail))
            return Response({"detail": detail}, status=status.HTTP_502_BAD_GATEWAY)

        return Response(summary, status=status.HTTP_200_OK)

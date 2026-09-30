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
from apps.billing.services.regularization import (
    RegularizationError,
    regularize_with_credit_card,
)
from apps.billing.services.subscription_cancel import cancel_tenant_subscription
from apps.billing.services.subscription_reactivate import (
    ReactivationCardError,
    ReactivationDebtError,
    ReactivationError,
    reactivate_tenant_subscription,
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


def _card_payload(request) -> tuple[dict, dict, str]:
    serializer = UpdatePaymentMethodSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    card = dict(serializer.validated_data["credit_card"])
    holder = dict(serializer.validated_data["credit_card_holder"])
    if not (holder.get("cpfCnpj") or "").strip():
        holder.pop("cpfCnpj", None)
    forwarded = (request.META.get("HTTP_X_FORWARDED_FOR") or "").split(",")[0].strip()
    remote_ip = forwarded or request.META.get("REMOTE_ADDR") or ""
    return card, holder, remote_ip


class RegularizeView(BillingSettingsBaseView):
    """Paga com cartão a(s) cobrança(s) exigida(s); libera o acesso só com a confirmação."""

    def post(self, request):
        tenant = self._tenant_or_error(request)
        if isinstance(tenant, Response):
            return tenant

        card, holder, remote_ip = _card_payload(request)
        try:
            result = regularize_with_credit_card(tenant, card, holder, remote_ip)
        except RegularizationError as exc:
            return Response({"detail": exc.detail, "code": exc.code}, status=exc.http_status)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_404_NOT_FOUND)
        except AsaasAPIError as exc:
            logger.warning("Asaas regularize: %s", exc.payload or exc)
            return Response(
                {"detail": "Não foi possível processar o pagamento agora.", "code": "gateway_error"},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        if result.status == "regularized":
            return Response(
                {
                    "status": "regularized",
                    "detail": "Pagamento confirmado. Seu acesso foi liberado.",
                    "paid_charges": result.paid_charges,
                },
                status=status.HTTP_200_OK,
            )
        return Response(
            {
                "status": "pending_confirmation",
                "detail": (
                    "Pagamento enviado e aguardando confirmação da operadora. "
                    "O acesso é liberado automaticamente assim que for aprovado."
                ),
                "paid_charges": result.paid_charges,
                "pending_charges": result.pending_charges,
            },
            status=status.HTTP_202_ACCEPTED,
        )


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

        card, holder, remote_ip = _card_payload(request)

        try:
            summary = update_subscription_card(
                tenant,
                card,
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


class CancelSubscriptionView(BillingSettingsBaseView):
    def post(self, request):
        tenant = self._tenant_or_error(request)
        if isinstance(tenant, Response):
            return tenant

        if tenant.subscription_status == Tenant.SubscriptionStatus.CANCELED:
            return Response(
                {"detail": "A assinatura já está cancelada."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            cancel_tenant_subscription(tenant)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_404_NOT_FOUND)
        except AsaasAPIError as exc:
            logger.warning("Asaas cancel subscription: %s", exc.payload or exc)
            detail = "Não foi possível cancelar a assinatura."
            if exc.payload and isinstance(exc.payload, dict):
                errors = exc.payload.get("errors")
                if errors:
                    detail = str(errors[0].get("description", detail))
            return Response({"detail": detail}, status=status.HTTP_502_BAD_GATEWAY)

        return Response(
            {
                "detail": "Assinatura cancelada. Você não será cobrado nas próximas faturas.",
                "subscription_canceled": True,
            },
            status=status.HTTP_200_OK,
        )


class ReactivateSubscriptionView(BillingSettingsBaseView):
    def post(self, request):
        tenant = self._tenant_or_error(request)
        if isinstance(tenant, Response):
            return tenant

        if tenant.subscription_status != Tenant.SubscriptionStatus.CANCELED:
            return Response(
                {"detail": "A assinatura não está cancelada."},
                status=status.HTTP_409_CONFLICT,
            )

        try:
            reactivate_tenant_subscription(tenant)
            summary = get_payment_method_summary(tenant)
        except ReactivationDebtError as exc:
            return Response(
                {"detail": str(exc), "code": "outstanding_debt"},
                status=status.HTTP_409_CONFLICT,
            )
        except ReactivationError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except ReactivationCardError as exc:
            return Response(
                {
                    "detail": (
                        "Não foi possível reativar com o cartão atual. "
                        "Por favor, insira um novo cartão de crédito para reativar seu plano."
                    ),
                    "code": "card_required",
                },
                status=status.HTTP_402_PAYMENT_REQUIRED,
            )
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_404_NOT_FOUND)
        except AsaasAPIError as exc:
            logger.warning("Asaas reactivate subscription: %s", exc.payload or exc)
            detail = "Não foi possível reativar a assinatura."
            if exc.payload and isinstance(exc.payload, dict):
                errors = exc.payload.get("errors")
                if errors:
                    detail = str(errors[0].get("description", detail))
            return Response({"detail": detail}, status=status.HTTP_502_BAD_GATEWAY)

        return Response(
            {
                "detail": "Assinatura reativada com sucesso.",
                **summary,
            },
            status=status.HTTP_200_OK,
        )

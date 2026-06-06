from __future__ import annotations

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import IsTenantAdmin
from apps.financial.serializers import (
    LedgerTransactionSerializer,
    WalletSettingsSerializer,
    WithdrawRequestSerializer,
)
from apps.financial.services.asaas_transfers import AsaasTransferError
from apps.financial.models import Wallet
from apps.financial.validators.pix_key import mask_pix_key_for_display
from apps.financial.services.wallet import (
    InsufficientBalanceError,
    WalletError,
    get_statement,
    request_withdrawal,
    update_wallet_pix_settings,
    withdrawal_success_message,
)


def _wallet_settings_payload(wallet, *, for_get: bool = False) -> dict:
    key = wallet.default_pix_key or ""
    key_type = wallet.default_pix_key_type or ""
    configured = wallet.has_default_pix_key
    masked = mask_pix_key_for_display(key_type, key) if configured else ""

    if for_get and configured:
        exposed_key = ""
    else:
        exposed_key = key

    return {
        "default_pix_key": exposed_key,
        "default_pix_key_type": key_type,
        "default_pix_key_masked": masked,
        "has_pix_key_configured": configured,
    }


class FinancialStatementView(APIView):
    permission_classes = [IsAuthenticated, IsTenantAdmin]

    def get(self, request: Request) -> Response:
        tenant_id = getattr(request.user, "tenant_id", None)
        if not tenant_id:
            return Response({"detail": "Conta sem empresa vinculada."}, status=400)

        try:
            page = max(1, int(request.query_params.get("page", 1)))
        except (TypeError, ValueError):
            page = 1

        statement = get_statement(tenant_id, page=page)
        return Response(
            {
                "balance_available": str(statement.balance_available),
                "balance_blocked": str(statement.balance_blocked),
                "balance_processing": str(statement.balance_processing),
                "fee_percent": float(statement.fee_percent),
                "page": statement.page,
                "total_count": statement.total_count,
                "next": statement.next_page,
                "previous": statement.previous_page,
                "results": LedgerTransactionSerializer(statement.results, many=True).data,
                **_wallet_settings_payload(statement.wallet),
            },
        )


class FinancialWalletSettingsView(APIView):
    permission_classes = [IsAuthenticated, IsTenantAdmin]

    def get(self, request: Request) -> Response:
        tenant_id = getattr(request.user, "tenant_id", None)
        if not tenant_id:
            return Response({"detail": "Conta sem empresa vinculada."}, status=400)

        wallet, _created = Wallet.get_or_create_for_tenant(tenant_id)
        return Response(_wallet_settings_payload(wallet, for_get=True))

    def patch(self, request: Request) -> Response:
        tenant_id = getattr(request.user, "tenant_id", None)
        if not tenant_id:
            return Response({"detail": "Conta sem empresa vinculada."}, status=400)

        ser = WalletSettingsSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data

        try:
            wallet = update_wallet_pix_settings(
                tenant_id=tenant_id,
                pix_key=data["default_pix_key"],
                pix_key_type=data["default_pix_key_type"],
            )
        except AsaasTransferError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except WalletError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(_wallet_settings_payload(wallet))


class FinancialWithdrawView(APIView):
    permission_classes = [IsAuthenticated, IsTenantAdmin]

    def post(self, request: Request) -> Response:
        tenant_id = getattr(request.user, "tenant_id", None)
        if not tenant_id:
            return Response({"detail": "Conta sem empresa vinculada."}, status=400)

        ser = WithdrawRequestSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data

        try:
            withdrawal = request_withdrawal(
                tenant_id=tenant_id,
                amount=data["amount"],
            )
        except InsufficientBalanceError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except AsaasTransferError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except WalletError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(
            {
                "withdrawal_id": withdrawal.id,
                "status": withdrawal.status,
                "message": withdrawal_success_message(withdrawal.status),
            },
            status=status.HTTP_201_CREATED,
        )

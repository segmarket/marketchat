from __future__ import annotations

from decimal import Decimal, InvalidOperation

from rest_framework import serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.billing.services.chat_pix_charge import ChatPixChargeError, generate_chat_pix_charge
from apps.billing.services.chat_pix_whatsapp_delivery import deliver_chat_pix_charge_messages
from apps.tenants.context import tenant_scope


class ChatPixItemSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255)
    quantity = serializers.IntegerField(min_value=1)
    unit_price = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal("0.01"))


class ChatPixChargeSerializer(serializers.Serializer):
    session_id = serializers.IntegerField(min_value=1)
    items = ChatPixItemSerializer(many=True, required=False)
    amount = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        required=False,
        allow_null=True,
        min_value=Decimal("0.01"),
    )
    description = serializers.CharField(required=False, allow_blank=True, max_length=500)
    deliver_whatsapp = serializers.BooleanField(required=False, default=False)

    def validate(self, attrs: dict) -> dict:
        amount = attrs.get("amount")
        items = attrs.get("items") or []
        if amount is None and not items:
            raise serializers.ValidationError(
                "Informe 'amount' (valor avulso) ou a lista 'items'.",
            )
        return attrs


class GenerateChatPixView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request: Request) -> Response:
        tenant_id = getattr(request.user, "tenant_id", None)
        if not tenant_id:
            return Response({"detail": "Conta sem empresa vinculada."}, status=400)

        serializer = ChatPixChargeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        amount = data.get("amount")
        if amount is not None:
            try:
                amount = Decimal(amount).quantize(Decimal("0.01"))
            except (InvalidOperation, TypeError, ValueError):
                return Response({"detail": "Valor inválido."}, status=400)

        items = data.get("items")
        # amount avulso tem prioridade (conforme plano).
        if amount is not None:
            items = None

        try:
            with tenant_scope(int(tenant_id)):
                result = generate_chat_pix_charge(
                    tenant_id=int(tenant_id),
                    session_id=int(data["session_id"]),
                    items=items,
                    amount=amount,
                    description=data.get("description") or "",
                )
                delivered = False
                if data.get("deliver_whatsapp"):
                    deliver_chat_pix_charge_messages(
                        tenant_id=int(tenant_id),
                        session_id=int(data["session_id"]),
                        summary_text=result["message_summary"],
                        pix_code=result["message_pix"],
                    )
                    delivered = True
        except ChatPixChargeError as exc:
            return Response({"detail": str(exc)}, status=400)

        return Response(
            {
                "pix_copia_e_cola": result["pix_copia_e_cola"],
                "invoice_url": result["invoice_url"],
                "amount": result["amount"],
                "cart_id": result["cart_id"],
                "description": result["description"],
                "items_summary": result["items_summary"],
                "billing_mode": result["billing_mode"],
                "message_summary": result["message_summary"],
                "message_pix": result["message_pix"],
                "delivered_whatsapp": delivered,
            },
            status=201,
        )

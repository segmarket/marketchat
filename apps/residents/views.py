import re

from django.db.models import Q
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.markets.models import Market
from apps.residents.models import Resident
from apps.residents.serializers import (
    ResidentMarketOptionSerializer,
    ResidentPatchSerializer,
    ResidentSerializer,
)


class ResidentListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        qs = Resident.objects.filter(market__isnull=False).select_related("market").order_by(
            "-created_at"
        )
        market_id = request.query_params.get("market_id")
        if market_id:
            try:
                qs = qs.filter(market_id=int(market_id))
            except (TypeError, ValueError):
                return Response(
                    {"detail": "Parâmetro market_id inválido."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        name = (request.query_params.get("name") or "").strip()
        if name:
            qs = qs.filter(name__icontains=name)

        phone = re.sub(r"\D", "", request.query_params.get("phone") or "")
        if phone:
            qs = qs.filter(phone_number__icontains=phone)

        return Response(ResidentSerializer(qs, many=True).data)


class ResidentMarketListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        markets = Market.objects.filter(status=Market.Status.ACTIVE).order_by("name")
        return Response(ResidentMarketOptionSerializer(markets, many=True).data)


class ResidentDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request: Request, pk: int) -> Response:
        try:
            resident = Resident.objects.get(pk=pk, market__isnull=False)
        except Resident.DoesNotExist:
            return Response({"detail": "Morador não encontrado."}, status=404)

        ser = ResidentPatchSerializer(
            data=request.data,
            context={"tenant_id": request.user.tenant_id},
        )
        ser.is_valid(raise_exception=True)
        market = Market.objects.get(pk=ser.validated_data["market_id"])
        resident.market = market
        resident.save(update_fields=["market", "updated_at"])
        return Response(ResidentSerializer(resident).data)

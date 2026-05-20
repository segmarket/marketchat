from django.db import transaction

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.billing.services.subscription_sync import update_tenant_subscription_value
from apps.markets.models import Market
from apps.tenants.models import Tenant
from apps.markets.serializers import (
    MarketCreateSerializer,
    MarketSerializer,
    MarketWriteSerializer,
)


def _schedule_subscription_sync(tenant_id: int) -> None:
    def _sync() -> None:
        tenant = Tenant.objects.filter(pk=tenant_id).first()
        if tenant:
            update_tenant_subscription_value(tenant)

    transaction.on_commit(_sync)


class MarketListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        markets = Market.objects.order_by("name")

        name = (request.query_params.get("name") or "").strip()
        if name:
            markets = markets.filter(name__icontains=name)

        address = (request.query_params.get("address") or "").strip()
        if address:
            markets = markets.filter(address__icontains=address)

        status = (request.query_params.get("status") or "").strip()
        if status in (Market.Status.ACTIVE, Market.Status.INACTIVE):
            markets = markets.filter(status=status)

        return Response(MarketSerializer(markets, many=True).data)

    def post(self, request: Request) -> Response:
        ser = MarketCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data
        market = Market.objects.create(
            tenant_id=request.user.tenant_id,
            name=data["name"],
            address=data["address"],
            status=data.get("status", Market.Status.ACTIVE),
        )
        _schedule_subscription_sync(request.user.tenant_id)
        return Response(MarketSerializer(market).data, status=status.HTTP_201_CREATED)


class MarketDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def _get_market(self, pk: int) -> Market | None:
        try:
            return Market.objects.get(pk=pk)
        except Market.DoesNotExist:
            return None

    def get(self, request: Request, pk: int) -> Response:
        market = self._get_market(pk)
        if market is None:
            return Response({"detail": "Mercado não encontrado."}, status=404)
        return Response(MarketSerializer(market).data)

    def patch(self, request: Request, pk: int) -> Response:
        market = self._get_market(pk)
        if market is None:
            return Response({"detail": "Mercado não encontrado."}, status=404)

        ser = MarketWriteSerializer(data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data
        if not data:
            return Response(
                {"detail": "Informe ao menos um campo: name, address ou status."},
                status=400,
            )

        update_fields = []
        if "name" in data:
            market.name = data["name"]
            update_fields.append("name")
        if "address" in data:
            market.address = data["address"]
            update_fields.append("address")
        if "status" in data:
            market.status = data["status"]
            update_fields.append("status")

        if update_fields:
            update_fields.append("updated_at")
            market.save(update_fields=update_fields)
            _schedule_subscription_sync(market.tenant_id)

        return Response(MarketSerializer(market).data)

    def put(self, request: Request, pk: int) -> Response:
        market = self._get_market(pk)
        if market is None:
            return Response({"detail": "Mercado não encontrado."}, status=404)

        ser = MarketCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data
        market.name = data["name"]
        market.address = data["address"]
        market.status = data.get("status", Market.Status.ACTIVE)
        market.save(update_fields=["name", "address", "status", "updated_at"])
        _schedule_subscription_sync(market.tenant_id)
        return Response(MarketSerializer(market).data)

    def delete(self, request: Request, pk: int) -> Response:
        market = self._get_market(pk)
        if market is None:
            return Response({"detail": "Mercado não encontrado."}, status=404)
        tenant_id = market.tenant_id
        market.delete()
        _schedule_subscription_sync(tenant_id)
        return Response(status=status.HTTP_204_NO_CONTENT)

from __future__ import annotations

from decimal import Decimal

from rest_framework import serializers

from apps.sales.models import Cart
from apps.sales.services.dashboard_metrics import DashboardMetrics


class DashboardMetricsSerializer(serializers.Serializer):
    total_revenue = serializers.DecimalField(max_digits=14, decimal_places=2)
    total_orders = serializers.IntegerField()
    average_ticket = serializers.DecimalField(max_digits=14, decimal_places=2)
    conversion_rate = serializers.FloatField()
    abandoned_orders = serializers.IntegerField()

    @classmethod
    def from_metrics(cls, metrics: DashboardMetrics) -> dict:
        return cls(
            {
                "total_revenue": metrics.total_revenue,
                "total_orders": metrics.total_orders,
                "average_ticket": metrics.average_ticket,
                "conversion_rate": metrics.conversion_rate,
                "abandoned_orders": metrics.abandoned_orders,
            },
        ).data


class SalesOrderRowSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    resident_name = serializers.CharField()
    market_name = serializers.CharField()
    total_value = serializers.DecimalField(max_digits=14, decimal_places=2)
    status = serializers.CharField()
    created_at = serializers.DateTimeField()
    asaas_billing_id = serializers.CharField()
    security_photo_url = serializers.CharField()

    @classmethod
    def from_cart(cls, cart: Cart, *, security_photo_url: str = "") -> dict:
        resident = cart.resident
        market_name = ""
        if resident and resident.market_id and resident.market:
            market_name = resident.market.name or ""
        return cls(
            {
                "id": cart.id,
                "resident_name": (resident.name if resident else "") or "",
                "market_name": market_name,
                "total_value": cart.total_value,
                "status": cart.status,
                "created_at": cart.created_at,
                "asaas_billing_id": cart.asaas_billing_id or "",
                "security_photo_url": security_photo_url,
            },
        ).data


class CartItemDetailSerializer(serializers.Serializer):
    product_name = serializers.CharField()
    sku = serializers.CharField()
    quantity = serializers.IntegerField()
    unit_price = serializers.DecimalField(max_digits=14, decimal_places=2)
    subtotal = serializers.DecimalField(max_digits=14, decimal_places=2)
    product_image_url = serializers.CharField(allow_null=True)


class CartDetailSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    resident_name = serializers.CharField()
    resident_phone = serializers.CharField()
    market_name = serializers.CharField()
    status = serializers.CharField()
    total_value = serializers.DecimalField(max_digits=14, decimal_places=2)
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()
    asaas_billing_id = serializers.CharField()
    security_photo_url = serializers.CharField()
    items = CartItemDetailSerializer(many=True)

    @classmethod
    def from_cart(cls, cart: Cart, *, security_photo_url: str = "") -> dict:
        resident = cart.resident
        items = []
        for item in cart.items.select_related("product").all():
            subtotal = (item.unit_price * item.quantity).quantize(Decimal("0.01"))
            items.append(
                {
                    "product_name": item.product.name,
                    "sku": item.product.sku,
                    "quantity": item.quantity,
                    "unit_price": item.unit_price,
                    "subtotal": subtotal,
                    "product_image_url": None,
                },
            )
        market_name = ""
        if resident and resident.market_id and resident.market:
            market_name = resident.market.name or ""
        return cls(
            {
                "id": cart.id,
                "resident_name": (resident.name if resident else "") or "",
                "resident_phone": (resident.phone_number if resident else "") or "",
                "market_name": market_name,
                "status": cart.status,
                "total_value": cart.total_value,
                "created_at": cart.created_at,
                "updated_at": cart.updated_at,
                "asaas_billing_id": cart.asaas_billing_id or "",
                "security_photo_url": security_photo_url,
                "items": items,
            },
        ).data

from decimal import Decimal

from rest_framework import serializers

from apps.products.models import Product


class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = ("id", "sku", "name", "price", "status", "created_at", "updated_at")
        read_only_fields = ("id", "sku", "created_at", "updated_at")


class ProductPatchSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255, required=False)
    price = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        required=False,
        min_value=Decimal("0"),
    )
    status = serializers.ChoiceField(
        choices=Product.Status.choices,
        required=False,
    )


class ImportConfirmSerializer(serializers.Serializer):
    import_token = serializers.UUIDField()

from rest_framework import serializers

from apps.markets.models import Market
from apps.residents.models import Resident


class ResidentMarketSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()


class ResidentSerializer(serializers.ModelSerializer):
    market = ResidentMarketSerializer(read_only=True, allow_null=True)

    class Meta:
        model = Resident
        fields = ("id", "name", "phone_number", "market", "created_at")
        read_only_fields = fields


class ResidentMarketOptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Market
        fields = ("id", "name")


class ResidentPatchSerializer(serializers.Serializer):
    market_id = serializers.IntegerField()

    def validate_market_id(self, value: int) -> int:
        tenant_id = self.context.get("tenant_id")
        if not Market.objects.filter(pk=value, tenant_id=tenant_id, status=Market.Status.ACTIVE).exists():
            raise serializers.ValidationError("Mercado inválido ou inativo.")
        return value

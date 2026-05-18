from rest_framework import serializers

from apps.markets.models import Market


class MarketSerializer(serializers.ModelSerializer):
    class Meta:
        model = Market
        fields = ("id", "name", "address", "status", "created_at", "updated_at")
        read_only_fields = ("id", "created_at", "updated_at")


class MarketWriteSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255, required=False)
    address = serializers.CharField(required=False, allow_blank=False)
    status = serializers.ChoiceField(choices=Market.Status.choices, required=False)

    def validate_name(self, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise serializers.ValidationError("Nome do condomínio é obrigatório.")
        return stripped

    def validate_address(self, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise serializers.ValidationError("Endereço é obrigatório.")
        return stripped


class MarketCreateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255)
    address = serializers.CharField()
    status = serializers.ChoiceField(
        choices=Market.Status.choices,
        default=Market.Status.ACTIVE,
        required=False,
    )

    def validate_name(self, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise serializers.ValidationError("Nome do condomínio é obrigatório.")
        return stripped

    def validate_address(self, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise serializers.ValidationError("Endereço é obrigatório.")
        return stripped

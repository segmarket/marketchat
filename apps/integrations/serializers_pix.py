from rest_framework import serializers

from apps.billing.models import AsaasSubaccount
from apps.billing.services.market_address import digits_only


class PixConfigWriteSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255)
    email = serializers.EmailField()
    cpf_cnpj = serializers.CharField(max_length=18)
    pix_key_type = serializers.ChoiceField(choices=AsaasSubaccount.PixKeyType.choices)
    pix_key = serializers.CharField(max_length=255)

    def validate_name(self, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise serializers.ValidationError("Informe o nome do titular.")
        return stripped

    def validate_cpf_cnpj(self, value: str) -> str:
        doc = digits_only(value)
        if len(doc) not in (11, 14):
            raise serializers.ValidationError("Informe CPF (11 dígitos) ou CNPJ (14 dígitos).")
        return doc

    def validate_pix_key(self, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise serializers.ValidationError("Informe a chave Pix.")
        return stripped

from decimal import Decimal

from rest_framework import serializers

from apps.financial.choices import PixKeyType
from apps.financial.models import LedgerTransaction
from apps.financial.validators.pix_key import validate_pix_key_for_type


class LedgerTransactionSerializer(serializers.ModelSerializer):
    entry_type_label = serializers.SerializerMethodField()
    signed_amount = serializers.SerializerMethodField()

    class Meta:
        model = LedgerTransaction
        fields = (
            "id",
            "amount",
            "signed_amount",
            "entry_type",
            "entry_type_label",
            "description",
            "external_id",
            "created_at",
        )

    def get_entry_type_label(self, obj: LedgerTransaction) -> str:
        if obj.entry_type == LedgerTransaction.EntryType.INFLOW:
            return "Entrada"
        return "Saída"

    def get_signed_amount(self, obj: LedgerTransaction) -> str:
        prefix = "+" if obj.entry_type == LedgerTransaction.EntryType.INFLOW else "-"
        return f"{prefix}{obj.amount:.2f}"


class WithdrawRequestSerializer(serializers.Serializer):
    amount = serializers.DecimalField(max_digits=14, decimal_places=2, min_value=Decimal("0.01"))


class WalletSettingsSerializer(serializers.Serializer):
    default_pix_key_type = serializers.ChoiceField(choices=PixKeyType.choices)
    default_pix_key = serializers.CharField(max_length=255)

    def validate(self, attrs: dict) -> dict:
        key_type = attrs["default_pix_key_type"]
        raw = attrs["default_pix_key"]
        try:
            attrs["default_pix_key"] = validate_pix_key_for_type(key_type, raw)
        except ValueError as exc:
            raise serializers.ValidationError({"default_pix_key": str(exc)}) from exc
        return attrs

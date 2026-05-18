from __future__ import annotations

from rest_framework import serializers

from apps.accounts.serializers import CreditCardHolderSerializer, CreditCardSerializer


class UpdatePaymentMethodSerializer(serializers.Serializer):
    credit_card = CreditCardSerializer()
    credit_card_holder = CreditCardHolderSerializer()

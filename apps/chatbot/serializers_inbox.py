from rest_framework import serializers


class ChatSessionInboxRowSerializer(serializers.Serializer):
    session_id = serializers.IntegerField()
    resident_name = serializers.CharField()
    resident_phone = serializers.CharField()
    market_name = serializers.CharField()
    is_bot_active = serializers.BooleanField()
    last_at = serializers.DateTimeField()
    preview = serializers.CharField()
    last_direction = serializers.CharField(allow_blank=True)
    last_inbound_id = serializers.IntegerField(allow_null=True)

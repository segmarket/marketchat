from rest_framework import serializers

from apps.notifications.models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    market_name = serializers.SerializerMethodField()

    class Meta:
        model = Notification
        fields = (
            "id",
            "title",
            "message",
            "severity",
            "is_read",
            "created_at",
            "market_id",
            "market_name",
            "intent_type",
        )
        read_only_fields = fields

    def get_market_name(self, obj: Notification) -> str | None:
        if obj.market_id and obj.market is not None:
            name = (obj.market.name or "").strip()
            return name or None
        return None

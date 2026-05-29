from __future__ import annotations

from django.conf import settings
from rest_framework import serializers

from apps.support.models import SupportTicket, SupportTicketMessage


class SupportChatHistoryItemSerializer(serializers.Serializer):
    role = serializers.ChoiceField(choices=["user", "assistant"])
    content = serializers.CharField(max_length=2000, trim_whitespace=True)


class SupportChatSerializer(serializers.Serializer):
    message = serializers.CharField(max_length=2000, trim_whitespace=True)
    current_route = serializers.CharField(max_length=512, trim_whitespace=True)
    chat_history = SupportChatHistoryItemSerializer(many=True, required=False, default=list)

    def validate_chat_history(self, value):
        max_items = getattr(settings, "SUPPORT_COPILOT_HISTORY_MAX", 20)
        if len(value) > max_items:
            raise serializers.ValidationError(
                f"O histórico pode ter no máximo {max_items} mensagens."
            )
        return value


class SupportTicketCreateSerializer(serializers.Serializer):
    subject = serializers.CharField(max_length=200, trim_whitespace=True)
    description = serializers.CharField(max_length=8000, trim_whitespace=True)
    category_route = serializers.CharField(max_length=512, trim_whitespace=True)


class SupportTicketReplySerializer(serializers.Serializer):
    message = serializers.CharField(max_length=4000, trim_whitespace=True)


class SupportTicketUpdateSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=["RESOLVED", "CLOSED"])


class SupportTicketMessageSerializer(serializers.ModelSerializer):
    sender_email = serializers.EmailField(source="sender.email", read_only=True)
    sender_name = serializers.SerializerMethodField()

    class Meta:
        model = SupportTicketMessage
        fields = (
            "id",
            "sender_email",
            "sender_name",
            "is_from_admin",
            "message",
            "created_at",
        )

    def get_sender_name(self, obj: SupportTicketMessage) -> str:
        sender = obj.sender
        full = f"{sender.first_name or ''} {sender.last_name or ''}".strip()
        return full or sender.email


class SupportTicketListSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source="user.email", read_only=True)
    message_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = SupportTicket
        fields = (
            "id",
            "subject",
            "status",
            "priority",
            "category_route",
            "created_at",
            "updated_at",
            "user_email",
            "message_count",
        )


class SupportTicketDetailSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source="user.email", read_only=True)
    messages = SupportTicketMessageSerializer(many=True, read_only=True)

    class Meta:
        model = SupportTicket
        fields = (
            "id",
            "subject",
            "description",
            "status",
            "priority",
            "category_route",
            "created_at",
            "updated_at",
            "user_email",
            "messages",
        )

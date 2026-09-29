from __future__ import annotations

from django.urls import reverse
from rest_framework import serializers

from apps.chatbot.models import ChatMessageLog


class ChatAttendanceRowSerializer(serializers.Serializer):
    session_id = serializers.IntegerField()
    attendance_date = serializers.CharField()
    resident_name = serializers.CharField()
    resident_phone = serializers.CharField()
    market_name = serializers.CharField()
    intent_type = serializers.CharField()
    last_at = serializers.DateTimeField()
    message_count = serializers.IntegerField()
    preview = serializers.CharField()


class ChatLogMessageSerializer(serializers.ModelSerializer):
    attachment_url = serializers.SerializerMethodField()

    class Meta:
        model = ChatMessageLog
        fields = (
            "id",
            "direction",
            "message_text",
            "intent_type",
            "message_kind",
            "created_at",
            "attachment_url",
        )

    def get_attachment_url(self, obj: ChatMessageLog) -> str:
        if not obj.attachment:
            return ""
        path = reverse("chatbot-message-attachment", kwargs={"pk": obj.pk})
        request = self.context.get("request")
        if request:
            return request.build_absolute_uri(path)
        return path


class ChatConversationSerializer(serializers.Serializer):
    session_id = serializers.IntegerField()
    resident_name = serializers.CharField()
    resident_phone = serializers.CharField()
    market_name = serializers.CharField()
    attendance_date = serializers.CharField()
    is_bot_active = serializers.BooleanField()
    resident_billing_identified = serializers.BooleanField()
    last_human_interaction_at = serializers.DateTimeField(allow_null=True)
    messages = ChatLogMessageSerializer(many=True)

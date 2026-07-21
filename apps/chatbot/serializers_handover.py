from rest_framework import serializers


class ToggleBotSerializer(serializers.Serializer):
    is_bot_active = serializers.BooleanField()


class AgentMessageCreateSerializer(serializers.Serializer):
    text = serializers.CharField(min_length=1, max_length=4000)

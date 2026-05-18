from rest_framework import serializers

from apps.chatbot.flow_schema import validate_flow_data
from apps.chatbot.models import ChatbotWorkflow


class ChatbotWorkflowListSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatbotWorkflow
        fields = (
            "id",
            "name",
            "is_active",
            "is_system",
            "system_key",
            "created_at",
            "updated_at",
        )


class ChatbotWorkflowDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatbotWorkflow
        fields = (
            "id",
            "name",
            "is_active",
            "is_system",
            "system_key",
            "flow_data",
            "created_at",
            "updated_at",
        )


class ChatbotWorkflowSaveSerializer(serializers.Serializer):
    id = serializers.IntegerField(required=False, allow_null=True)
    name = serializers.CharField(max_length=255, required=False, allow_blank=True)
    is_active = serializers.BooleanField(required=False)
    flow_data = serializers.JSONField()

    def validate_flow_data(self, value):
        try:
            return validate_flow_data(value)
        except ValueError as exc:
            raise serializers.ValidationError(str(exc)) from exc

    def validate_name(self, value: str) -> str:
        cleaned = (value or "").strip()
        return cleaned or "Fluxo principal"


class ChatbotWorkflowPatchSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255, required=False, allow_blank=True)
    is_active = serializers.BooleanField(required=False)

    def validate(self, attrs: dict) -> dict:
        if not attrs:
            raise serializers.ValidationError("Informe name ou is_active.")
        if "name" in attrs:
            cleaned = (attrs["name"] or "").strip()
            if not cleaned:
                raise serializers.ValidationError({"name": "Nome não pode ser vazio."})
            attrs["name"] = cleaned
        return attrs

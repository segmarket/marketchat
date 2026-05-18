from rest_framework import serializers

from apps.integrations.models import WhatsappInstance


class WhatsappInstancePublicSerializer(serializers.ModelSerializer):
    has_instance = serializers.SerializerMethodField()
    connected = serializers.SerializerMethodField()

    class Meta:
        model = WhatsappInstance
        fields = (
            "has_instance",
            "instance_name",
            "connection_status",
            "connected",
            "is_active",
            "pair_phone",
            "updated_at",
        )
        read_only_fields = fields

    def get_has_instance(self, obj: WhatsappInstance) -> bool:
        return bool(obj and obj.is_active)

    def get_connected(self, obj: WhatsappInstance) -> bool:
        return obj.connection_status == WhatsappInstance.ConnectionStatus.OPEN


class WhatsappProvisionSerializer(serializers.Serializer):
    pair_phone = serializers.CharField(max_length=32, required=False, allow_blank=True, default="")


class WhatsappQrcodeResponseSerializer(serializers.Serializer):
    connected = serializers.BooleanField()
    qrcode_image = serializers.CharField(allow_blank=True)
    connection_status = serializers.CharField()


class WhatsappStatusResponseSerializer(serializers.Serializer):
    connection_status = serializers.CharField()
    connected = serializers.BooleanField()

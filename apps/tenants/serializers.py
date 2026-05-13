from rest_framework import serializers

from apps.tenants.models import DemoNote


class DemoNoteSerializer(serializers.ModelSerializer):
    class Meta:
        model = DemoNote
        fields = ("id", "title", "created_at", "updated_at")
        read_only_fields = ("id", "created_at", "updated_at")

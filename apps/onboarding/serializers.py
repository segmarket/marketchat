from rest_framework import serializers


class OnboardingStatusSerializer(serializers.Serializer):
    step_market_created = serializers.BooleanField()
    step_product_created = serializers.BooleanField()
    step_whatsapp_connected = serializers.BooleanField()
    step_test_order_completed = serializers.BooleanField()
    onboarding_finished = serializers.BooleanField()
    completed_count = serializers.IntegerField()
    completion_percent = serializers.IntegerField()
    show_mission_panel = serializers.BooleanField()

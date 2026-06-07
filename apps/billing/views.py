from django.conf import settings
from django.http import HttpResponse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.views import APIView

from apps.billing.services.asaas_webhook_payload import (
    extract_asaas_webhook_token,
    parse_http_request_body,
)
from apps.billing.services.webhook_processor import process_asaas_webhook_payload


@method_decorator(csrf_exempt, name="dispatch")
class AsaasWebhookView(APIView):
    """Recebe notificações do Asaas (sem JWT)."""

    authentication_classes: list = []
    permission_classes = [AllowAny]

    def post(self, request: Request) -> HttpResponse:
        if settings.ASAAS_WEBHOOK_VERIFY:
            token = extract_asaas_webhook_token(request)
            if not settings.ASAAS_WEBHOOK_TOKEN or token != settings.ASAAS_WEBHOOK_TOKEN:
                return HttpResponse(status=401)
        body = parse_http_request_body(request)
        process_asaas_webhook_payload(body)
        return HttpResponse(status=200)

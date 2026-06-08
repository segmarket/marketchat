from django.http import HttpResponse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.views import APIView

from apps.billing.services.asaas_webhook_auth import verify_asaas_webhook_request
from apps.billing.services.asaas_webhook_payload import parse_http_request_body
from apps.billing.services.webhook_processor import process_asaas_webhook_payload


@method_decorator(csrf_exempt, name="dispatch")
class AsaasWebhookView(APIView):
    """Recebe notificações do Asaas (sem JWT)."""

    authentication_classes: list = []
    permission_classes = [AllowAny]
    throttle_classes: list = []

    def post(self, request: Request) -> HttpResponse:
        if not verify_asaas_webhook_request(request):
            return HttpResponse(status=403)
        body = parse_http_request_body(request)
        process_asaas_webhook_payload(body)
        return HttpResponse(status=200)

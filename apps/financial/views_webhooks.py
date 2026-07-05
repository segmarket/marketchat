from django.http import HttpResponse, JsonResponse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.views import APIView

from apps.billing.services.asaas_webhook_payload import parse_http_request_body
from apps.financial.services.asaas_withdrawal_validation import (
    build_withdrawal_validation_response,
    verify_asaas_withdrawal_validation_request,
)


@method_decorator(csrf_exempt, name="dispatch")
class AsaasWithdrawalValidationWebhookView(APIView):
    """Validação automática de saques Pix solicitada pelo Asaas (~5s após criar transfer)."""

    authentication_classes: list = []
    permission_classes = [AllowAny]
    throttle_classes: list = []

    def post(self, request: Request) -> HttpResponse:
        if not verify_asaas_withdrawal_validation_request(request):
            return HttpResponse(status=403)

        body = parse_http_request_body(request)
        response_body = build_withdrawal_validation_response(body)
        return JsonResponse(response_body, status=200)

import logging

from django.conf import settings
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.integrations.models import WhatsappInstance
from apps.integrations.services.webhook_handlers import handle_evolution_webhook
from apps.integrations.services.webhook_parser import parse_evolution_payload

logger = logging.getLogger(__name__)


@method_decorator(csrf_exempt, name="dispatch")
class EvolutionWebhookView(APIView):
    authentication_classes: list = []
    permission_classes = [AllowAny]
    # Evolution dispara dezenas de eventos/minuto (MESSAGE, presença, conexão).
    # O throttle anon global (10/min) gerava 429 e descartava mensagens do morador
    # (ex.: resposta do nome no onboarding sem registro no histórico).
    throttle_classes: list = []

    def post(self, request: Request) -> Response:
        body = request.data if isinstance(request.data, dict) else {}
        event = parse_evolution_payload(body)
        if not event:
            return Response({"ok": True, "ignored": True})

        if event.from_me or (event.remote_jid and event.remote_jid.endswith("@g.us")):
            return Response({"ok": True})

        instance = self._resolve_instance(request, event.instance_key)
        if not instance:
            logger.warning(
                "Webhook Evolution: instância não encontrada (key=%r, has_secret=%s)",
                event.instance_key,
                bool(request.query_params.get("secret")),
            )
            return Response({"error": "unknown instance"}, status=404)

        if not self._allowed(request, instance):
            logger.warning(
                "Webhook Evolution forbidden: instance=%s event=%s "
                "query_secret=%s header_secret=%s apikey=%s",
                instance.instance_name,
                event.event_type,
                bool(request.query_params.get("secret")),
                bool(request.headers.get("X-Webhook-Secret")),
                bool(
                    request.headers.get("apikey")
                    or request.headers.get("Apikey")
                    or request.headers.get("APIKEY")
                ),
            )
            return Response({"error": "forbidden"}, status=403)

        try:
            handle_evolution_webhook(event, instance)
            instance.last_webhook_at = timezone.now()
            instance.save(update_fields=["last_webhook_at", "updated_at"])
        except Exception:
            logger.exception("Erro processando webhook Evolution")
            return Response({"error": "internal"}, status=500)

        return Response({"ok": True})

    def _resolve_instance(self, request: Request, instance_key: str) -> WhatsappInstance | None:
        qs = WhatsappInstance.all_objects.all()
        secret = request.query_params.get("secret")
        if secret:
            inst = qs.filter(webhook_secret=secret).order_by("-is_active", "-id").first()
            if inst:
                return inst
        apikey = self._request_apikey(request)
        if apikey:
            inst = qs.filter(api_key=apikey).order_by("-is_active", "-id").first()
            if inst:
                return inst
        active_qs = qs.filter(is_active=True)
        if not instance_key:
            return None
        inst = active_qs.filter(instance_name=instance_key).first()
        if inst:
            return inst
        inst = qs.filter(instance_name=instance_key).order_by("-id").first()
        if inst:
            return inst
        return active_qs.filter(instance_id=instance_key).first() or qs.filter(
            instance_id=instance_key
        ).order_by("-id").first()

    @staticmethod
    def _request_apikey(request: Request) -> str:
        return (
            request.headers.get("apikey")
            or request.headers.get("Apikey")
            or request.headers.get("APIKEY")
            or ""
        ).strip()

    def _allowed(self, request: Request, instance: WhatsappInstance) -> bool:
        secret = (
            request.headers.get("X-Webhook-Secret")
            or request.query_params.get("secret")
            or ""
        ).strip()
        apikey = self._request_apikey(request)

        if instance.webhook_secret and secret == instance.webhook_secret:
            return True
        if instance.api_key and apikey and apikey == instance.api_key:
            return True

        if instance.webhook_secret or instance.api_key:
            return False

        global_secret = getattr(settings, "WEBHOOK_SHARED_SECRET", "") or ""
        if global_secret:
            return bool(secret) and secret == global_secret
        return bool(settings.DEBUG)

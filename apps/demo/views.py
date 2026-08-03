import logging

from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.demo.services.chat import (
    DEMO_EMPTY_REPLY_FALLBACK,
    DEMO_MEDIA_MARKER,
    normalize_session_id,
    process_demo_chat_turn,
)
from apps.demo.throttling import DemoChatThrottle

logger = logging.getLogger(__name__)


def _coerce_bool(value) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "sim"}
    return False


class DemoChatAPIView(APIView):
    """Degustação pública do chatbot (tenant Portal) — sem Evolution."""

    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [DemoChatThrottle]

    def post(self, request):
        message = (request.data.get("message") or "").strip()
        session_id = request.data.get("session_id") or ""
        is_media = _coerce_bool(request.data.get("is_media"))
        if is_media and not message:
            message = DEMO_MEDIA_MARKER
        if not message and not is_media:
            return Response(
                {"detail": "Campo message é obrigatório."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if len(message) > 2000:
            return Response(
                {"detail": "Mensagem muito longa."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            result = process_demo_chat_turn(
                message=message,
                session_id=session_id or None,
                is_media=is_media,
            )
        except Exception:
            logger.exception("demo_chat view: falha inesperada")
            sid = normalize_session_id(session_id or None)
            result = {"reply": DEMO_EMPTY_REPLY_FALLBACK, "session_id": sid}
        if not (result.get("reply") or "").strip():
            result = {
                **result,
                "reply": DEMO_EMPTY_REPLY_FALLBACK,
                "session_id": result.get("session_id")
                or normalize_session_id(session_id or None),
            }
        return Response(result, status=status.HTTP_200_OK)

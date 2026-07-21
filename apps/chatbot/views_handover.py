"""Endpoints de Human Handover (toggle bot + mensagem do atendente)."""

from __future__ import annotations

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.chatbot.serializers_chat_logs import ChatLogMessageSerializer
from apps.chatbot.serializers_handover import (
    AgentMessageCreateSerializer,
    ToggleBotSerializer,
)
from apps.chatbot.services.chat_logging import log_agent_outbound
from apps.chatbot.services.human_handover import pause_bot, toggle_bot
from apps.integrations.services.instance_lookup import get_active_whatsapp_instance
from apps.residents.models import ChatSession
from apps.residents.services.whatsapp_reply import send_whatsapp_reply
from apps.tenants.context import tenant_scope


def _tenant_id(request: Request) -> int | None:
    tid = getattr(request.user, "tenant_id", None)
    return int(tid) if tid else None


def _get_session(tenant_id: int, session_id: int) -> ChatSession | None:
    return ChatSession.objects.filter(tenant_id=tenant_id, pk=session_id).first()


def _bot_status_payload(session: ChatSession) -> dict:
    return {
        "is_bot_active": session.is_bot_active,
        "last_human_interaction_at": session.last_human_interaction_at,
    }


class ChatSessionToggleBotView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request: Request, pk: int) -> Response:
        tenant_id = _tenant_id(request)
        if not tenant_id:
            return Response(
                {"detail": "Conta sem empresa vinculada."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = ToggleBotSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        with tenant_scope(tenant_id):
            session = _get_session(tenant_id, pk)
            if session is None:
                return Response(
                    {"detail": "Sessão não encontrada."},
                    status=status.HTTP_404_NOT_FOUND,
                )
            toggle_bot(
                session,
                is_bot_active=serializer.validated_data["is_bot_active"],
            )
            session.refresh_from_db()
            return Response(_bot_status_payload(session))


class ChatSessionAgentMessageView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request: Request, pk: int) -> Response:
        tenant_id = _tenant_id(request)
        if not tenant_id:
            return Response(
                {"detail": "Conta sem empresa vinculada."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = AgentMessageCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        text = serializer.validated_data["text"].strip()

        with tenant_scope(tenant_id):
            session = _get_session(tenant_id, pk)
            if session is None:
                return Response(
                    {"detail": "Sessão não encontrada."},
                    status=status.HTTP_404_NOT_FOUND,
                )

            instance = get_active_whatsapp_instance(tenant_id)
            if instance is None:
                return Response(
                    {"detail": "Nenhuma instância WhatsApp ativa."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            try:
                send_whatsapp_reply(
                    instance,
                    session.phone_number,
                    text,
                    session=session,
                    log_message=False,
                    record_context=False,
                )
            except Exception:
                return Response(
                    {"detail": "Falha ao enviar mensagem no WhatsApp."},
                    status=status.HTTP_502_BAD_GATEWAY,
                )

            log = log_agent_outbound(
                instance=instance,
                phone=session.phone_number,
                message_text=text,
                session=session,
            )
            pause_bot(session)
            session.refresh_from_db()

            payload = {
                **_bot_status_payload(session),
                "message": (
                    ChatLogMessageSerializer(log, context={"request": request}).data
                    if log
                    else None
                ),
            }
            return Response(payload, status=status.HTTP_201_CREATED)

"""Envio sequencial da cobrança PIX do chat no WhatsApp (2 mensagens)."""

from __future__ import annotations

import logging

from apps.billing.services.chat_pix_charge import ChatPixChargeError
from apps.chatbot.services.chat_logging import log_agent_outbound
from apps.chatbot.services.human_handover import pause_bot
from apps.integrations.services.instance_lookup import get_active_whatsapp_instance
from apps.residents.models import ChatSession
from apps.residents.services.whatsapp_reply import send_whatsapp_reply
from apps.sales.services.chat_fsm import transition

logger = logging.getLogger(__name__)


def deliver_chat_pix_charge_messages(
    *,
    tenant_id: int,
    session_id: int,
    summary_text: str,
    pix_code: str,
) -> None:
    session = ChatSession.objects.filter(tenant_id=tenant_id, pk=session_id).first()
    if session is None:
        raise ChatPixChargeError("Conversa não encontrada.")

    instance = get_active_whatsapp_instance(tenant_id)
    if instance is None:
        raise ChatPixChargeError("Nenhuma instância WhatsApp ativa.")

    phone = session.phone_number
    summary = (summary_text or "").strip()
    pix = (pix_code or "").strip()
    if not summary or not pix:
        raise ChatPixChargeError("Textos de envio da cobrança inválidos.")

    try:
        send_whatsapp_reply(
            instance,
            phone,
            summary,
            session=session,
            log_message=False,
            record_context=False,
        )
    except Exception as exc:
        logger.exception("Falha ao enviar resumo PIX no chat: session=%s", session_id)
        raise ChatPixChargeError("Falha ao enviar resumo da cobrança no WhatsApp.") from exc

    log_agent_outbound(
        instance=instance,
        phone=phone,
        message_text=summary,
        session=session,
    )

    try:
        send_whatsapp_reply(
            instance,
            phone,
            pix,
            session=session,
            log_message=False,
            record_context=False,
        )
    except Exception as exc:
        logger.exception(
            "Falha ao enviar código PIX no chat (resumo já enviado): session=%s",
            session_id,
        )
        raise ChatPixChargeError(
            "O resumo foi enviado, mas o código PIX não. "
            "Reenvie o código manualmente ou gere uma nova cobrança.",
        ) from exc

    log_agent_outbound(
        instance=instance,
        phone=phone,
        message_text=pix,
        session=session,
    )

    pause_bot(session)
    if session.state == ChatSession.State.WAITING_FOR_HUMAN:
        transition(session, ChatSession.State.IDLE, reason="agent_assumed")

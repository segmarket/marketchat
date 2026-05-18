from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from apps.integrations.services.evolution_client import EvolutionClient

if TYPE_CHECKING:
    from apps.integrations.models import WhatsappInstance
    from apps.residents.models import ChatSession
    from apps.sales.models import Cart

logger = logging.getLogger(__name__)


def send_whatsapp_reply(
    instance: WhatsappInstance,
    phone: str,
    text: str,
    *,
    intent_type: str = "",
    session: ChatSession | None = None,
    cart: Cart | None = None,
    log_message: bool = True,
) -> None:
    """Envia mensagem de texto via Evolution GO e registra no log de atendimento."""
    digits = "".join(c for c in phone if c.isdigit())
    if not digits or not text.strip():
        return
    client = EvolutionClient()
    try:
        client.send_text(
            instance_api_key=instance.api_key,
            number=digits,
            text=text,
        )
    except Exception:
        logger.exception(
            "Falha ao enviar WhatsApp: tenant=%s phone=%s",
            instance.tenant_id,
            digits,
        )
        raise

    if log_message:
        from apps.chatbot.services.chat_logging import log_outbound

        log_outbound(
            instance=instance,
            phone=phone,
            message_text=text,
            intent_type=intent_type,
            session=session,
            cart=cart,
        )

    if session is not None:
        from apps.residents.services.session_activity import touch_chat_session_activity

        touch_chat_session_activity(session)

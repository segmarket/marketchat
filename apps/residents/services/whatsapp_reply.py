from __future__ import annotations

import logging
from contextlib import contextmanager
from contextvars import ContextVar
from typing import TYPE_CHECKING, Iterator

from apps.integrations.services.evolution_client import EvolutionClient

if TYPE_CHECKING:
    from apps.integrations.models import WhatsappInstance
    from apps.residents.models import ChatSession
    from apps.sales.models import Cart

logger = logging.getLogger(__name__)

# Quando setado (lista), send_whatsapp_reply apenas coleta textos — sem Evolution.
_demo_reply_collector: ContextVar[list[str] | None] = ContextVar(
    "demo_reply_collector",
    default=None,
)


@contextmanager
def capture_demo_replies() -> Iterator[list[str]]:
    """Captura replies do bot sem enviar via Evolution API."""
    bucket: list[str] = []
    token = _demo_reply_collector.set(bucket)
    try:
        yield bucket
    finally:
        _demo_reply_collector.reset(token)


def send_whatsapp_reply(
    instance: WhatsappInstance,
    phone: str,
    text: str,
    *,
    intent_type: str = "",
    session: ChatSession | None = None,
    cart: Cart | None = None,
    log_message: bool = True,
    record_context: bool = True,
) -> None:
    """Envia mensagem de texto via Evolution GO (ou coleta no sink de demo)."""
    digits = "".join(c for c in phone if c.isdigit())
    body = (text or "").strip()
    if not digits or not body:
        return

    collector = _demo_reply_collector.get()
    if collector is not None:
        collector.append(body)
        if session is not None:
            from apps.residents.services.session_activity import touch_chat_session_activity

            touch_chat_session_activity(session)
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

    if record_context and body:
        from apps.chatbot.services.chat_context_cache import append_message

        append_message(
            instance.tenant_id,
            phone,
            role="assistant",
            content=body,
        )

    if session is not None:
        from apps.residents.services.session_activity import touch_chat_session_activity

        touch_chat_session_activity(session)

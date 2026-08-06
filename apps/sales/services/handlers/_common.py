"""Helpers compartilhados pelos handlers do menu de suporte."""

from __future__ import annotations

from apps.integrations.models import WhatsappInstance
from apps.residents.models import ChatSession
from apps.residents.services.whatsapp_reply import send_whatsapp_reply
from apps.sales.services.chat_fsm import transition
from apps.sales.services.whatsapp_interactive import SUPPORT_DETAILS_PROMPT


def start_support_details_collection(
    *,
    instance: WhatsappInstance,
    phone: str,
    session: ChatSession,
    choice: str,
    reason: str,
) -> None:
    """Persiste a categoria do menu e pede detalhes ao morador."""
    session.temporary_name = choice
    session.save(update_fields=["temporary_name", "updated_at"])
    transition(session, ChatSession.State.AWAITING_SUPPORT_DETAILS, reason=reason)
    send_whatsapp_reply(instance, phone, SUPPORT_DETAILS_PROMPT, session=session)

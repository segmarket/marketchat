"""Handler de produto sem cadastro (opção 2)."""

from __future__ import annotations

from apps.integrations.models import WhatsappInstance
from apps.residents.models import ChatSession, Resident
from apps.residents.services.whatsapp_reply import send_whatsapp_reply
from apps.sales.services.chat_fsm import transition
from apps.sales.services.whatsapp_interactive import (
    MENU_UNCATALOGUED,
    UNREGISTERED_PRODUCT_SEARCH_PROMPT,
)


def handle_missing_product(
    *,
    instance: WhatsappInstance,
    phone: str,
    resident: Resident,
    session: ChatSession,
    text: str = "",
    choice_code: str = MENU_UNCATALOGUED,
) -> bool:
    """Opção 2 — inicia busca de produto não cadastrado."""
    del text, resident, choice_code
    session.temporary_name = ""
    session.save(update_fields=["temporary_name", "updated_at"])
    transition(
        session,
        ChatSession.State.SEARCHING_UNREGISTERED_PRODUCT,
        reason="main_menu_uncatalogued",
    )
    send_whatsapp_reply(
        instance,
        phone,
        UNREGISTERED_PRODUCT_SEARCH_PROMPT,
        session=session,
    )
    return True

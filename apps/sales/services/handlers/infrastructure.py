"""Handlers de infraestrutura (opções 4 geladeira e 5 loja)."""

from __future__ import annotations

from apps.integrations.models import WhatsappInstance
from apps.residents.models import ChatSession, Resident
from apps.sales.services.handlers._common import start_support_details_collection
from apps.sales.services.whatsapp_interactive import MENU_FRIDGE, MENU_STORE

_REASON_BY_CHOICE = {
    MENU_FRIDGE: "main_menu_fridge",
    MENU_STORE: "main_menu_store",
}


def handle_infrastructure_issue(
    *,
    instance: WhatsappInstance,
    phone: str,
    resident: Resident,
    session: ChatSession,
    text: str = "",
    choice_code: str,
) -> bool:
    """Opções 4/5 — coleta detalhes para fila humana."""
    del text, resident
    start_support_details_collection(
        instance=instance,
        phone=phone,
        session=session,
        choice=choice_code,
        reason=_REASON_BY_CHOICE.get(choice_code, "main_menu_support"),
    )
    return True

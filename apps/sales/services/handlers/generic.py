"""Handler genérico — outros assuntos (opção 7)."""

from __future__ import annotations

from apps.integrations.models import WhatsappInstance
from apps.residents.models import ChatSession, Resident
from apps.sales.services.handlers._common import start_support_details_collection
from apps.sales.services.whatsapp_interactive import MENU_OTHER


def handle_generic_issue(
    *,
    instance: WhatsappInstance,
    phone: str,
    resident: Resident,
    session: ChatSession,
    text: str = "",
    choice_code: str = MENU_OTHER,
) -> bool:
    """Opção 7 — coleta detalhes para fila humana."""
    del text, resident
    start_support_details_collection(
        instance=instance,
        phone=phone,
        session=session,
        choice=choice_code or MENU_OTHER,
        reason="main_menu_other",
    )
    return True

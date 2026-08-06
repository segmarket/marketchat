"""Handler de problema com produto (opção 6)."""

from __future__ import annotations

from apps.integrations.models import WhatsappInstance
from apps.residents.models import ChatSession, Resident
from apps.sales.services.handlers._common import start_support_details_collection
from apps.sales.services.whatsapp_interactive import MENU_PRODUCT


def handle_quality_issue(
    *,
    instance: WhatsappInstance,
    phone: str,
    resident: Resident,
    session: ChatSession,
    text: str = "",
    choice_code: str = MENU_PRODUCT,
) -> bool:
    """Opção 6 — coleta detalhes (ex.: vencido/estragado) para fila humana."""
    del text, resident
    start_support_details_collection(
        instance=instance,
        phone=phone,
        session=session,
        choice=choice_code or MENU_PRODUCT,
        reason="main_menu_product_issue",
    )
    return True

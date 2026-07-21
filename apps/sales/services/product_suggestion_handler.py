"""Registro de sugestão de produto pelo morador."""

from __future__ import annotations

import logging

from apps.integrations.models import WhatsappInstance
from apps.notifications.services import create_product_suggestion_notification
from apps.residents.models import ChatSession, Resident
from apps.residents.services.whatsapp_reply import send_whatsapp_reply
from apps.sales.services.chat_fsm import reset_to_idle
from apps.sales.services.owner_alert import notify_owner_product_suggestion
from apps.sales.services.product_term_extractor import (
    ProductTermExtractorError,
    extract_product_term,
)
from apps.sales.services.resident_ai_context import resident_display_name, resident_market_name

logger = logging.getLogger(__name__)

PRODUCT_SUGGESTION_INTENT = "PRODUCT_SUGGESTION"


def extract_suggestion_label(message: str) -> str:
    try:
        term = extract_product_term(message)
        if term and term.strip().upper() != "NONE":
            return term.strip()
    except ProductTermExtractorError:
        logger.debug("Não foi possível extrair produto da sugestão.")
    cleaned = (message or "").strip()
    if cleaned:
        return cleaned[:120]
    return "produto não identificado"


def build_suggestion_resident_message(*, resident: Resident, product_label: str) -> str:
    name = resident_display_name(resident)
    market = resident_market_name(resident)
    product = product_label.strip() or "sua sugestão"
    return (
        f"Obrigado, {name}! 📝 Anotei a sugestão de incluir {product} "
        f"no mercado do {market}. Vou encaminhar para o responsável avaliar. "
        "Posso ajudar com mais alguma coisa?"
    )


def handle_product_suggestion(
    *,
    instance: WhatsappInstance,
    resident: Resident,
    phone: str,
    message: str,
    session: ChatSession,
) -> bool:
    product_label = extract_suggestion_label(message)
    reply = build_suggestion_resident_message(
        resident=resident,
        product_label=product_label,
    )
    send_whatsapp_reply(
        instance,
        phone,
        reply,
        intent_type=PRODUCT_SUGGESTION_INTENT,
        session=session,
    )
    notify_owner_product_suggestion(
        instance=instance,
        resident=resident,
        product_label=product_label,
        original_message=message,
    )
    create_product_suggestion_notification(
        tenant_id=resident.tenant_id,
        resident=resident,
        product_label=product_label,
        original_message=message,
    )
    reset_to_idle(session, reason="product_suggestion_recorded")
    return True

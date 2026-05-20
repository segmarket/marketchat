"""Resposta padronizada para relatos de produto em falta."""

from __future__ import annotations

import logging

from apps.integrations.models import WhatsappInstance
from apps.residents.models import ChatSession, Resident
from apps.residents.services.whatsapp_reply import send_whatsapp_reply
from apps.sales.services.chat_fsm import record_discussed_product
from apps.sales.services.product_search import search_active_products
from apps.sales.services.owner_alert import notify_owner_restock_issue
from apps.sales.services.product_term_extractor import (
    ProductTermExtractorError,
    extract_product_term,
)
from apps.sales.services.resident_ai_context import resident_display_name, resident_market_name

logger = logging.getLogger(__name__)


def extract_stock_product_label(message: str) -> str:
    """Nome do produto citado no relato de falta."""
    try:
        term = extract_product_term(message)
        if term and term.strip().upper() != "NONE":
            return term.strip()
    except ProductTermExtractorError:
        logger.debug("Não foi possível extrair produto do relato de estoque.")
    return "o produto"


def build_stock_issue_resident_message(*, resident: Resident, product_label: str) -> str:
    name = resident_display_name(resident)
    market = resident_market_name(resident)
    product = product_label.strip() or "o produto"
    return (
        f"Putz, obrigado por avisar, {name}! 📝 Já anotei aqui que {product} está em falta "
        f"no mercado do {market}. Vou encaminhar agora mesmo para o responsável providenciar "
        "a reposição o quanto antes! Posso ajudar com mais alguma coisa?"
    )


def handle_stock_issue_report(
    *,
    instance: WhatsappInstance,
    resident: Resident,
    phone: str,
    message: str,
    session: ChatSession | None = None,
) -> None:
    product_label = extract_stock_product_label(message)
    if session is None:
        session = (
            ChatSession.objects.filter(
                tenant_id=resident.tenant_id,
                phone_number=phone,
            )
            .first()
        )
    if session and product_label != "o produto":
        matches = search_active_products(resident.tenant_id, product_label)
        if matches:
            record_discussed_product(session, matches[0])
    reply = build_stock_issue_resident_message(
        resident=resident,
        product_label=product_label,
    )
    send_whatsapp_reply(instance, phone, reply)
    notify_owner_restock_issue(
        instance=instance,
        resident=resident,
        product_label=product_label,
        original_message=message,
    )

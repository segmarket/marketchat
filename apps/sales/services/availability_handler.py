"""Perguntas de disponibilidade no catálogo (ex.: 'tem coca?')."""

from __future__ import annotations

import logging

from apps.integrations.models import WhatsappInstance
from apps.residents.models import ChatSession, Resident
from apps.residents.services.whatsapp_reply import send_whatsapp_reply
from apps.sales.services.chat_fsm import record_discussed_product
from apps.sales.services.product_search import search_active_products
from apps.sales.services.product_term_extractor import (
    ProductTermExtractorError,
    extract_product_term,
)
from apps.sales.services.purchase_context import looks_like_availability_question
from apps.sales.services.whatsapp_interactive import send_product_list

logger = logging.getLogger(__name__)


def handle_availability_question(
    *,
    tenant_id: int,
    instance: WhatsappInstance,
    phone: str,
    resident: Resident,
    session: ChatSession,
    text: str,
) -> bool:
    """
    Responde disponibilidade sem OpenAI genérica e grava last_discussed_product.
  """
    if not looks_like_availability_question(text):
        return False

    try:
        term = extract_product_term(text)
    except ProductTermExtractorError:
        return False

    from apps.sales.services.product_search import is_product_term_none

    if is_product_term_none(term):
        return False

    products = search_active_products(tenant_id, term)
    if not products:
        send_whatsapp_reply(
            instance,
            phone,
            f'No momento não encontrei "{term}" no catálogo. Quer tentar outro nome?',
        )
        return True

    record_discussed_product(session, products[0])

    if len(products) == 1:
        product = products[0]
        send_whatsapp_reply(
            instance,
            phone,
            f"Sim! Temos {product.name} disponível. "
            f"Se quiser levar, digite *quero comprar* ou o nome do produto.",
        )
        return True

    send_whatsapp_reply(
        instance,
        phone,
        f'Encontrei opções para "{term}". Qual você prefere?',
    )
    send_product_list(instance, phone, products)
    return True

"""Despacho de alertas e ações FSM a partir de tags de ocorrência da IA."""

from __future__ import annotations

import logging

from apps.integrations.models import WhatsappInstance
from apps.notifications.services import create_occurrence_notification
from apps.residents.models import ChatSession, Resident
from apps.sales.services.cart_repository import get_or_create_open_cart
from apps.sales.services.owner_alert import notify_owner_restock_issue, notify_owner_support_issue
from apps.sales.services.product_term_extractor import (
    ProductTermExtractorError,
    extract_product_term,
)
from apps.sales.services.stock_issue_handler import extract_stock_product_label

logger = logging.getLogger(__name__)

_OWNER_LABELS: dict[str, str] = {
    "ALERTA_QUALIDADE": "Qualidade alimentar",
    "ALERTA_INFRA": "Infraestrutura",
    "ALERTA_CATALOGO": "Catálogo/preço",
    "ALERTA_MAQUININHA": "Maquininha",
}


def _start_product_search_flow(session: ChatSession, resident: Resident) -> None:
    """Abre carrinho e inicia busca de produtos (Pix / maquininha / solicitação direta)."""
    cart = get_or_create_open_cart(resident)
    session.active_cart = cart
    session.temporary_name = ""
    session.pending_product = None
    session.state = ChatSession.State.PRODUCT_SEARCH
    session.save(
        update_fields=[
            "active_cart",
            "temporary_name",
            "pending_product",
            "state",
            "updated_at",
        ],
    )


def _extract_product_from_message(message: str) -> str:
    try:
        return extract_stock_product_label(message)
    except Exception:
        return "o produto"


def dispatch_occurrence_tag(
    *,
    tag: str,
    tenant_id: int,
    instance: WhatsappInstance,
    resident: Resident,
    session: ChatSession,
    user_message: str,
    owner_pre_notified: bool = False,
) -> None:
    """Notifica painel/dono e aplica transições FSM conforme a tag."""
    create_occurrence_notification(
        tenant_id=tenant_id,
        resident=resident,
        tag=tag,
        original_message=user_message,
    )

    if tag == "ALERTA_ESTOQUE":
        product_label = _extract_product_from_message(user_message)
        if not owner_pre_notified:
            notify_owner_restock_issue(
                instance=instance,
                resident=resident,
                product_label=product_label,
                original_message=user_message,
            )
        _record_discussed_product_safe(session, user_message)
        return

    if tag in ("ALERTA_MAQUININHA", "AJUDA_LEITURA"):
        _start_product_search_flow(session, resident)
    elif tag == "SOLICITACAO_PIX":
        _start_product_search_flow(session, resident)
        from apps.sales.services.pix_hurry_cart import apply_pix_hurry_from_message

        apply_pix_hurry_from_message(session, resident, user_message)

    if tag == "FEEDBACK_PRECO":
        return

    if owner_pre_notified:
        return

    label = _OWNER_LABELS.get(tag)
    if label:
        notify_owner_support_issue(
            instance=instance,
            tenant_id=tenant_id,
            resident=resident,
            original_message=user_message,
            issue_label=label,
        )


def _record_discussed_product_safe(session: ChatSession, message: str) -> None:
    try:
        from apps.sales.services.chat_fsm import record_discussed_product
        from apps.sales.services.product_search import search_active_products

        term = extract_product_term(message)
        if not term or term.strip().upper() == "NONE":
            return
        products = search_active_products(session.tenant_id, term)
        if products:
            record_discussed_product(session, products[0])
    except (ProductTermExtractorError, Exception):
        logger.debug("Não foi possível gravar last_discussed_product para tag de estoque.")

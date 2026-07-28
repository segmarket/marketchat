"""Opção 2 do menu: produto sem cadastro na maquininha — busca e retenção."""

from __future__ import annotations

from apps.chatbot.services.human_handover import resume_bot
from apps.integrations.models import WhatsappInstance
from apps.residents.models import ChatSession, Resident
from apps.residents.services.whatsapp_reply import send_whatsapp_reply
from apps.sales.services.cart_escape import is_global_escape_message
from apps.sales.services.cart_repository import get_or_create_open_cart
from apps.sales.services.chat_fsm import (
    clear_product_search_context,
    record_discussed_product,
    transition,
)
from apps.sales.services.owner_alert import notify_owner_support_issue
from apps.sales.services.product_search import search_active_products
from apps.sales.services.whatsapp_interactive import (
    UNREGISTERED_PRODUCT_NOT_FOUND_MESSAGE,
    UNREGISTERED_PRODUCT_SEARCH_PROMPT,
    build_uncatalogued_product_found_message,
)


def _save_product_skus(session: ChatSession, products) -> None:
    session.temporary_name = ",".join(p.sku for p in products[:10])
    session.save(update_fields=["temporary_name", "updated_at"])


def handle_uncatalogued_product_search(
    *,
    tenant_id: int,
    instance: WhatsappInstance,
    phone: str,
    resident: Resident,
    session: ChatSession,
    text: str,
) -> bool:
    if is_global_escape_message(text):
        from apps.sales.services.main_menu import show_main_menu

        show_main_menu(
            instance=instance,
            phone=phone,
            resident=resident,
            session=session,
        )
        return True

    term = (text or "").strip()
    if not term:
        send_whatsapp_reply(
            instance,
            phone,
            UNREGISTERED_PRODUCT_SEARCH_PROMPT,
            session=session,
        )
        return True

    products = search_active_products(tenant_id, term)
    if products:
        clear_product_search_context(session, clear_discussed=False, clear_pending=True)
        if len(products) == 1:
            record_discussed_product(session, products[0])

        cart = get_or_create_open_cart(resident)
        session.active_cart = cart
        transition(session, ChatSession.State.PRODUCT_SEARCH, reason="uncatalogued_found")
        session.pending_product = None
        _save_product_skus(session, products)
        session.save(update_fields=["active_cart", "pending_product", "updated_at"])

        send_whatsapp_reply(
            instance,
            phone,
            build_uncatalogued_product_found_message(products),
            session=session,
        )
        return True

    notify_owner_support_issue(
        instance=instance,
        tenant_id=tenant_id,
        resident=resident,
        original_message=term,
        issue_label="Produto sem cadastro",
    )
    transition(session, ChatSession.State.WAITING_FOR_HUMAN, reason="uncatalogued_not_found")
    if not session.is_bot_active:
        resume_bot(session)
    send_whatsapp_reply(
        instance,
        phone,
        UNREGISTERED_PRODUCT_NOT_FOUND_MESSAGE,
        session=session,
    )
    return True

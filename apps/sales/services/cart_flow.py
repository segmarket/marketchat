from __future__ import annotations

import logging
from decimal import Decimal

from apps.chatbot.services.human_handover import resume_bot
from apps.integrations.models import WhatsappInstance
from apps.integrations.services.message_interactive import event_has_image
from apps.integrations.services.webhook_parser import EvolutionWebhookEvent
from apps.products.models import Product
from apps.residents.models import ChatSession, Resident
from apps.residents.services.onboarding_flow import resident_has_completed_onboarding
from apps.residents.services.whatsapp_reply import send_whatsapp_reply
from apps.sales.models import Cart, CartItem
from apps.sales.services.active_bot_router import (
    handle_complaint,
    handle_maintenance_issue,
    handle_payment_error_pivot,
    handle_stock_issue,
    route_idle_message,
)
from apps.sales.services.availability_handler import handle_availability_question
from apps.sales.services.cart_escape import (
    CHECKOUT_PHOTO_MESSAGE,
    LOOP_DECISION_FALLBACK,
    handle_global_escape,
    is_global_escape_message,
    resolve_loop_choice_from_text,
    should_escape_product_search_for_intent,
    try_checkout_from_text,
)
from apps.sales.services.cart_repository import get_or_create_open_cart
from apps.sales.services.chat_fsm import (
    clear_product_search_context,
    record_discussed_product,
    transition,
)
from apps.sales.services.product_selection import (
    PRODUCT_SELECTION_ESCAPE_REPLY,
    PRODUCT_SELECTION_INVALID_REPLY,
    is_likely_new_product_search_text,
    is_product_selection_escape,
)
from apps.sales.services.evolution_media import save_cart_photo_from_webhook
from apps.sales.services.intent_gatekeeper import (
    COMPLAINT,
    MAINTENANCE_ISSUE,
    STOCK_ISSUE,
    classify_user_intent,
)
from apps.sales.services.main_menu import handle_main_menu_message, show_main_menu
from apps.sales.services.product_suggestion_handler import handle_product_suggestion
from apps.sales.services.uncatalogued_product_flow import handle_uncatalogued_product_search
from apps.sales.services.product_search import (
    ASK_PRODUCT_MESSAGE,
    MAIN_MENU_PURCHASE_PROMPT,
    is_product_term_none,
    search_active_products,
)
from apps.sales.services.product_term_extractor import (
    ProductTermExtractorError,
    extract_product_term,
)
from apps.sales.services.purchase_context import is_purchase_without_product
from apps.sales.services.whatsapp_interactive import (
    CART_ADD_MORE,
    CART_CHECKOUT,
    MENU_PAYMENT,
    PROD_ID_PREFIX,
    SUPPORT_WAITING_QUEUE_MESSAGE,
    parse_numeric_product_choice,
    send_cart_decision_buttons,
    send_product_list,
)

logger = logging.getLogger(__name__)

CART_SESSION_STATES = frozenset(
    {
        ChatSession.State.PRODUCT_SEARCH,
        ChatSession.State.QUANTITY_SELECTION,
        ChatSession.State.CART_REVIEW,
        ChatSession.State.AWAITING_PHOTO,
    },
)


def _format_brl(value: Decimal) -> str:
    return f"R$ {value:.2f}".replace(".", ",")


def _get_or_create_session(tenant_id: int, phone: str) -> ChatSession:
    session, _ = ChatSession.objects.get_or_create(
        tenant_id=tenant_id,
        phone_number=phone,
        defaults={"state": ChatSession.State.IDLE},
    )
    return session


def _save_product_skus(session: ChatSession, products: list[Product]) -> None:
    session.temporary_name = ",".join(p.sku for p in products[:10])
    session.save(update_fields=["temporary_name", "updated_at"])


def _load_products_from_session(session: ChatSession, tenant_id: int) -> list[Product]:
    skus = [s.strip() for s in session.temporary_name.split(",") if s.strip()]
    if not skus:
        return []
    rows = Product.objects.filter(
        tenant_id=tenant_id,
        sku__in=skus,
        status=Product.Status.ACTIVE,
    )
    by_sku = {p.sku: p for p in rows}
    return [by_sku[sku] for sku in skus if sku in by_sku]


def _resolve_interactive_id(
    event: EvolutionWebhookEvent,
    session: ChatSession,
    tenant_id: int,
) -> str:
    if event.interactive_id:
        return event.interactive_id
    text = (event.message_text or "").strip()
    if session.state == ChatSession.State.PRODUCT_SEARCH:
        products = _load_products_from_session(session, tenant_id)
        return parse_numeric_product_choice(text, products) or ""
    if session.state == ChatSession.State.CART_REVIEW:
        return resolve_loop_choice_from_text(text) or ""
    return ""


def _handle_support_details(
    *,
    instance: WhatsappInstance,
    phone: str,
    resident: Resident,
    session: ChatSession,
    text: str,
) -> bool:
    """
    Opção 1 = pivot pagamento.
    Opções 2–7 = classifica o detalhe (COMPLAINT/manutenção/estoque),
    dispara alertas internos e entra na fila de espera ativa.
    """
    category = (session.temporary_name or "").strip()
    session.temporary_name = ""
    session.save(update_fields=["temporary_name", "updated_at"])

    if category == MENU_PAYMENT:
        return handle_payment_error_pivot(
            instance=instance,
            tenant_id=session.tenant_id,
            phone=phone,
            resident=resident,
            session=session,
            message=text,
        )

    intent = classify_user_intent(
        text,
        tenant_id=session.tenant_id,
        phone=phone,
    )
    handler_kwargs = {
        "instance": instance,
        "tenant_id": session.tenant_id,
        "phone": phone,
        "resident": resident,
        "session": session,
        "message": text,
        "queue_for_human": True,
    }
    if intent == COMPLAINT:
        handle_complaint(**handler_kwargs)
    elif intent == MAINTENANCE_ISSUE:
        handle_maintenance_issue(**handler_kwargs)
    elif intent == STOCK_ISSUE:
        handle_stock_issue(**handler_kwargs)

    transition(session, ChatSession.State.WAITING_FOR_HUMAN, reason="support_waiting_queue")
    if not session.is_bot_active:
        resume_bot(session)
    send_whatsapp_reply(
        instance,
        phone,
        SUPPORT_WAITING_QUEUE_MESSAGE,
        session=session,
    )
    return True


def process_cart_flow(
    tenant_id: int,
    instance: WhatsappInstance,
    phone: str,
    event: EvolutionWebhookEvent,
) -> bool:
    """Processa máquina de estados do carrinho. Retorna True se tratou a mensagem."""
    if not resident_has_completed_onboarding(tenant_id, phone):
        return False

    resident = (
        Resident.objects.filter(
            tenant_id=tenant_id,
            phone_number=phone,
            market__isnull=False,
        )
        .select_related("market")
        .first()
    )
    if not resident:
        return False

    text = (event.message_text or "").strip()
    session = _get_or_create_session(tenant_id, phone)

    if session.state == ChatSession.State.WAITING_FOR_HUMAN and text:
        if is_global_escape_message(text):
            show_main_menu(
                instance=instance,
                phone=phone,
                resident=resident,
                session=session,
            )
            return True
        return True

    if text and handle_global_escape(
        instance=instance,
        phone=phone,
        resident=resident,
        text=text,
    ):
        return True

    interactive_id = _resolve_interactive_id(event, session, tenant_id)

    if text and try_checkout_from_text(
        instance=instance,
        phone=phone,
        resident=resident,
        session=session,
        text=text,
    ):
        return True

    if session.state in CART_SESSION_STATES:
        return _dispatch_cart_state(
            tenant_id,
            instance,
            phone,
            event,
            resident,
            session,
            text,
            interactive_id,
        )

    if session.state == ChatSession.State.AWAITING_MAIN_MENU and (text or interactive_id):
        return handle_main_menu_message(
            instance=instance,
            phone=phone,
            resident=resident,
            session=session,
            text=text,
            interactive_id=interactive_id,
        )

    if session.state == ChatSession.State.SEARCHING_UNREGISTERED_PRODUCT and text:
        return handle_uncatalogued_product_search(
            tenant_id=tenant_id,
            instance=instance,
            phone=phone,
            resident=resident,
            session=session,
            text=text,
        )

    if session.state == ChatSession.State.AWAITING_SUPPORT_DETAILS and text:
        return _handle_support_details(
            instance=instance,
            phone=phone,
            resident=resident,
            session=session,
            text=text,
        )

    if session.state == ChatSession.State.AWAITING_PRODUCT_SUGGESTION and text:
        return handle_product_suggestion(
            instance=instance,
            resident=resident,
            phone=phone,
            message=text,
            session=session,
        )

    if session.state == ChatSession.State.IDLE:
        if event.message_kind == "interactive" or interactive_id:
            return _dispatch_cart_state(
                tenant_id,
                instance,
                phone,
                event,
                resident,
                session,
                text,
                interactive_id,
            )
        if text:
            return route_idle_message(
                tenant_id=tenant_id,
                instance=instance,
                phone=phone,
                resident=resident,
                session=session,
                message=text,
                on_purchase=lambda: _handle_idle_purchase(
                    tenant_id, instance, phone, resident, session, text,
                ),
            )

    return False


def _route_product_search_intent_escape(
    tenant_id: int,
    instance: WhatsappInstance,
    phone: str,
    resident: Resident,
    session: ChatSession,
    text: str,
) -> bool:
    """Sai de PRODUCT_SEARCH e delega ao gatekeeper em IDLE."""
    transition(session, ChatSession.State.IDLE, reason="product_search_intent_escape")
    logger.info(
        "PRODUCT_SEARCH escape para gatekeeper: tenant=%s phone=%s text_len=%s",
        tenant_id,
        phone,
        len(text),
    )
    return route_idle_message(
        tenant_id=tenant_id,
        instance=instance,
        phone=phone,
        resident=resident,
        session=session,
        message=text,
        on_purchase=lambda: _handle_idle_purchase(
            tenant_id, instance, phone, resident, session, text,
        ),
    )


def _handle_idle_purchase(
    tenant_id: int,
    instance: WhatsappInstance,
    phone: str,
    resident: Resident,
    session: ChatSession,
    text: str,
) -> bool:
    """PURCHASE em IDLE: slot fill com last_discussed_product ou busca normal."""
    if is_purchase_without_product(text) and session.last_discussed_product_id:
        product = session.last_discussed_product
        transition(session, ChatSession.State.PRODUCT_SEARCH, reason="slot_fill_discussed")
        return _handle_product_search(
            tenant_id,
            instance,
            phone,
            resident,
            session,
            product.name,
        )
    return _handle_product_search(
        tenant_id, instance, phone, resident, session, text,
    )


def _dispatch_cart_state(
    tenant_id: int,
    instance: WhatsappInstance,
    phone: str,
    event: EvolutionWebhookEvent,
    resident: Resident,
    session: ChatSession,
    text: str,
    interactive_id: str,
) -> bool:
    if session.state == ChatSession.State.PRODUCT_SEARCH:
        if interactive_id and interactive_id.startswith(PROD_ID_PREFIX):
            return _handle_product_selection(
                tenant_id, instance, phone, resident, session, text, interactive_id,
            )
        if text.strip():
            list_handled = _handle_active_product_list_input(
                tenant_id,
                instance,
                phone,
                resident,
                session,
                text.strip(),
            )
            if list_handled is True:
                return True
            if should_escape_product_search_for_intent(text):
                return _route_product_search_intent_escape(
                    tenant_id,
                    instance,
                    phone,
                    resident,
                    session,
                    text.strip(),
                )
            return _handle_product_search(
                tenant_id, instance, phone, resident, session, text.strip(),
            )
        send_whatsapp_reply(instance, phone, "Digite o nome do produto que deseja buscar.")
        return True

    if session.state == ChatSession.State.QUANTITY_SELECTION:
        return _handle_quantity(instance, phone, resident, session, text)

    if session.state == ChatSession.State.CART_REVIEW:
        return _handle_loop_decision(instance, phone, resident, session, interactive_id, text)

    if session.state == ChatSession.State.AWAITING_PHOTO:
        return _handle_photo(instance, phone, resident, session, event)

    if session.state == ChatSession.State.IDLE and interactive_id:
        if interactive_id.startswith(PROD_ID_PREFIX):
            return _handle_product_selection(
                tenant_id, instance, phone, resident, session, text, interactive_id,
            )
    return False


def _handle_active_product_list_input(
    tenant_id: int,
    instance: WhatsappInstance,
    phone: str,
    resident: Resident,
    session: ChatSession,
    text: str,
) -> bool | None:
    """
    Trata mensagem quando há lista numerada pendente (temporary_name com SKUs).
    Retorna True se tratou, False se deve seguir para nova busca, None se não há lista.
    """
    products = _load_products_from_session(session, tenant_id)
    if not products:
        return None

    if is_product_selection_escape(text):
        clear_product_search_context(session, clear_discussed=True)
        transition(session, ChatSession.State.PRODUCT_SEARCH, reason="product_list_escape")
        send_whatsapp_reply(instance, phone, PRODUCT_SELECTION_ESCAPE_REPLY)
        return True

    stripped = text.strip()
    if stripped.isdigit():
        idx = int(stripped)
        if 1 <= idx <= len(products):
            row_id = f"{PROD_ID_PREFIX}{products[idx - 1].sku}"
            return _handle_product_selection(
                tenant_id,
                instance,
                phone,
                resident,
                session,
                text,
                row_id,
            )
        send_whatsapp_reply(instance, phone, PRODUCT_SELECTION_INVALID_REPLY)
        return True

    if is_likely_new_product_search_text(text):
        clear_product_search_context(session, clear_discussed=True)
        return False

    send_whatsapp_reply(instance, phone, PRODUCT_SELECTION_INVALID_REPLY)
    return True


def _handle_product_search(
    tenant_id: int,
    instance: WhatsappInstance,
    phone: str,
    resident: Resident,
    session: ChatSession,
    text: str,
) -> bool:
    if handle_global_escape(
        instance=instance,
        phone=phone,
        resident=resident,
        text=text,
    ):
        return True

    try:
        term = extract_product_term(text)
    except ProductTermExtractorError:
        send_whatsapp_reply(
            instance,
            phone,
            "Não entendi o produto. Digite o nome, ex.: coca cola.",
        )
        return True

    if is_product_term_none(term):
        if session.last_discussed_product_id:
            term = session.last_discussed_product.name
        elif is_global_escape_message(text):
            return handle_global_escape(
                instance=instance,
                phone=phone,
                resident=resident,
                text=text,
            )
        else:
            cart = get_or_create_open_cart(resident)
            session.active_cart = cart
            transition(
                session,
                ChatSession.State.PRODUCT_SEARCH,
                reason="purchase_without_term",
            )
            session.pending_product = None
            session.temporary_name = ""
            session.save(
                update_fields=[
                    "active_cart",
                    "pending_product",
                    "temporary_name",
                    "updated_at",
                ],
            )
            send_whatsapp_reply(instance, phone, ASK_PRODUCT_MESSAGE)
            return True

    clear_product_search_context(session, clear_discussed=False, clear_pending=True)

    products = search_active_products(tenant_id, term)
    if not products:
        send_whatsapp_reply(
            instance,
            phone,
            f'Não encontrei "{term}" no catálogo. Tente outro nome de produto.',
        )
        return True

    if len(products) == 1:
        record_discussed_product(session, products[0])

    cart = get_or_create_open_cart(resident)
    session.active_cart = cart
    transition(session, ChatSession.State.PRODUCT_SEARCH, reason="search_results")
    session.pending_product = None
    _save_product_skus(session, products)
    session.save(update_fields=["active_cart", "pending_product", "updated_at"])

    send_product_list(instance, phone, products)
    return True


def _handle_product_selection(
    tenant_id: int,
    instance: WhatsappInstance,
    phone: str,
    resident: Resident,
    session: ChatSession,
    text: str,
    interactive_id: str,
) -> bool:
    row_id = interactive_id
    if not row_id.startswith(PROD_ID_PREFIX):
        send_whatsapp_reply(instance, phone, "Selecione um produto da lista enviada.")
        return True

    sku = row_id[len(PROD_ID_PREFIX) :]
    product = Product.objects.filter(
        tenant_id=tenant_id,
        sku=sku,
        status=Product.Status.ACTIVE,
    ).first()
    if not product:
        send_whatsapp_reply(instance, phone, "Produto não encontrado. Busque novamente.")
        transition(session, ChatSession.State.IDLE, reason="product_not_found")
        return True

    record_discussed_product(session, product)
    cart = session.active_cart or get_or_create_open_cart(resident)
    session.active_cart = cart
    CartItem.objects.update_or_create(
        cart=cart,
        product=product,
        defaults={
            "quantity": 0,
            "unit_price": product.price,
        },
    )
    session.pending_product = product
    transition(session, ChatSession.State.QUANTITY_SELECTION, reason="product_selected")
    session.save(update_fields=["active_cart", "pending_product", "updated_at"])

    send_whatsapp_reply(
        instance,
        phone,
        f"Perfeito! Quantas unidades de {product.name} você vai levar? "
        "(Digite apenas o número ou digite Cancelar para recomeçar).",
    )
    return True


def _handle_quantity(
    instance: WhatsappInstance,
    phone: str,
    resident: Resident,
    session: ChatSession,
    text: str,
) -> bool:
    if not text.isdigit():
        send_whatsapp_reply(
            instance,
            phone,
            "Digite apenas um número inteiro para a quantidade, ou *Cancelar* para desistir.",
        )
        return True

    try:
        qty = int(text)
    except ValueError:
        send_whatsapp_reply(instance, phone, "Quantidade inválida.")
        return True

    if qty < 1 or qty > 999:
        send_whatsapp_reply(instance, phone, "Informe uma quantidade entre 1 e 999.")
        return True

    cart = session.active_cart
    product = session.pending_product
    if not cart or not product:
        send_whatsapp_reply(instance, phone, "Sessão expirada. Digite o que deseja comprar.")
        transition(session, ChatSession.State.IDLE, reason="quantity_session_expired")
        return True

    item = CartItem.objects.filter(cart=cart, product=product).first()
    if not item:
        send_whatsapp_reply(instance, phone, "Item não encontrado. Comece uma nova busca.")
        transition(session, ChatSession.State.IDLE, reason="quantity_item_missing")
        return True

    item.quantity = qty
    item.save(update_fields=["quantity"])
    cart.recalculate_total()
    subtotal = item.subtotal

    session.pending_product = None
    transition(session, ChatSession.State.CART_REVIEW, reason="quantity_set")

    send_cart_decision_buttons(
        instance,
        phone,
        product_name=product.name,
        quantity=qty,
        subtotal=subtotal,
    )
    return True


def _handle_loop_decision(
    instance: WhatsappInstance,
    phone: str,
    resident: Resident,
    session: ChatSession,
    interactive_id: str,
    text: str,
) -> bool:
    choice = interactive_id or resolve_loop_choice_from_text(text)
    if not choice:
        send_whatsapp_reply(instance, phone, LOOP_DECISION_FALLBACK)
        return True

    if choice == CART_ADD_MORE:
        clear_product_search_context(session, clear_discussed=True)
        transition(
            session,
            ChatSession.State.PRODUCT_SEARCH,
            reason="add_more_items",
            clear_pending=True,
        )
        send_whatsapp_reply(instance, phone, MAIN_MENU_PURCHASE_PROMPT)
        return True

    if choice == CART_CHECKOUT:
        cart = session.active_cart
        if not cart:
            cart = get_or_create_open_cart(resident)
            session.active_cart = cart
            session.save(update_fields=["active_cart", "updated_at"])
        cart.recalculate_total()
        if cart.total_value <= Decimal("0"):
            send_whatsapp_reply(instance, phone, "Seu carrinho está vazio. Adicione itens primeiro.")
            return True

        cart.status = Cart.Status.AWAITING_PHOTO
        cart.save(update_fields=["status", "updated_at"])
        transition(session, ChatSession.State.AWAITING_PHOTO, reason="checkout")

        send_whatsapp_reply(instance, phone, CHECKOUT_PHOTO_MESSAGE)
        return True

    return False


def _handle_photo(
    instance: WhatsappInstance,
    phone: str,
    resident: Resident,
    session: ChatSession,
    event: EvolutionWebhookEvent,
) -> bool:
    cart = session.active_cart
    if not cart or cart.status != Cart.Status.AWAITING_PHOTO:
        send_whatsapp_reply(instance, phone, "Não há pagamento pendente de foto.")
        return True

    is_image = event_has_image(
        message_kind=event.message_kind,
        raw_message=event.raw_message,
    )
    if not is_image:
        text = (event.message_text or "").strip()
        if not text:
            logger.info(
                "AWAITING_PHOTO: evento sem imagem ignorado tenant=%s phone=%s kind=%s",
                instance.tenant_id,
                phone,
                event.message_kind,
            )
            return True
        send_whatsapp_reply(instance, phone, "Envie uma foto dos produtos para continuar.")
        return True

    raw = event.raw_message or {}
    if not save_cart_photo_from_webhook(
        instance=instance,
        cart=cart,
        raw_message=raw,
        evolution_message_id=event.message_id or "",
    ):
        send_whatsapp_reply(
            instance,
            phone,
            "Não consegui salvar a foto. Envie outra imagem, por favor.",
        )
        return True

    from apps.billing.services.asaas_pix_charge import PixChargeError, create_cart_pix_charge

    try:
        pix_code = create_cart_pix_charge(cart, resident)
    except PixChargeError as exc:
        send_whatsapp_reply(instance, phone, str(exc))
        return True

    transition(session, ChatSession.State.IDLE, reason="pix_sent")

    send_whatsapp_reply(
        instance,
        phone,
        (
            f"Para pagar {_format_brl(cart.total_value)}, copie o código Pix "
            "na próxima mensagem e cole no app do seu banco."
        ),
    )
    # Mensagem só com o código — mais fácil de selecionar/copiar no WhatsApp.
    send_whatsapp_reply(instance, phone, pix_code)
    return True

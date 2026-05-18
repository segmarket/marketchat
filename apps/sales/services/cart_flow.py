from __future__ import annotations

import logging
from decimal import Decimal

from apps.integrations.models import WhatsappInstance
from apps.integrations.services.message_interactive import event_has_image
from apps.integrations.services.webhook_parser import EvolutionWebhookEvent
from apps.products.models import Product
from apps.residents.models import ChatSession, Resident
from apps.residents.services.onboarding_flow import resident_has_completed_onboarding
from apps.residents.services.whatsapp_reply import send_whatsapp_reply
from apps.sales.models import Cart, CartItem
from apps.sales.services.active_bot_router import route_active_bot_message
from apps.sales.services.cart_escape import (
    LOOP_DECISION_FALLBACK,
    handle_global_escape,
    resolve_loop_choice_from_text,
)
from apps.sales.services.cart_repository import get_or_create_open_cart
from apps.sales.services.evolution_media import save_cart_photo_from_webhook
from apps.sales.services.product_search import (
    ASK_PRODUCT_MESSAGE,
    is_product_term_none,
    search_active_products,
)
from apps.sales.services.product_term_extractor import (
    ProductTermExtractorError,
    extract_product_term,
)
from apps.sales.services.whatsapp_interactive import (
    CART_ADD_MORE,
    CART_CHECKOUT,
    PROD_ID_PREFIX,
    parse_numeric_loop_choice,
    parse_numeric_product_choice,
    send_cart_decision_buttons,
    send_product_list,
)

logger = logging.getLogger(__name__)

CART_SESSION_STATES = frozenset(
    {
        ChatSession.State.AWAITING_PRODUCT_SELECTION,
        ChatSession.State.AWAITING_QUANTITY,
        ChatSession.State.AWAITING_LOOP_DECISION,
        ChatSession.State.AWAITING_PHOTO,
    },
)

def _format_brl(value: Decimal) -> str:
    return f"R$ {value:.2f}".replace(".", ",")


def _get_or_create_session(tenant_id: int, phone: str) -> ChatSession:
    session, _ = ChatSession.objects.get_or_create(
        tenant_id=tenant_id,
        phone_number=phone,
        defaults={"state": ChatSession.State.ACTIVE_BOT},
    )
    return session


def _save_product_skus(session: ChatSession, products: list[Product]) -> None:
    session.temporary_name = ",".join(p.sku for p in products[:10])
    session.save(update_fields=["temporary_name", "updated_at"])


def _load_products_from_session(session: ChatSession, tenant_id: int) -> list[Product]:
    skus = [s.strip() for s in session.temporary_name.split(",") if s.strip()]
    if not skus:
        return []
    return list(
        Product.objects.filter(tenant_id=tenant_id, sku__in=skus, status=Product.Status.ACTIVE),
    )


def _resolve_interactive_id(
    event: EvolutionWebhookEvent,
    session: ChatSession,
    tenant_id: int,
) -> str:
    if event.interactive_id:
        return event.interactive_id
    text = (event.message_text or "").strip()
    if session.state == ChatSession.State.AWAITING_PRODUCT_SELECTION:
        products = _load_products_from_session(session, tenant_id)
        return parse_numeric_product_choice(text, products) or ""
    if session.state == ChatSession.State.AWAITING_LOOP_DECISION:
        return resolve_loop_choice_from_text(text) or ""
    return ""


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

    if text and handle_global_escape(
        instance=instance,
        phone=phone,
        resident=resident,
        text=text,
    ):
        return True

    session = _get_or_create_session(tenant_id, phone)
    interactive_id = _resolve_interactive_id(event, session, tenant_id)

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

    if session.state == ChatSession.State.ACTIVE_BOT:
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
            return route_active_bot_message(
                tenant_id=tenant_id,
                instance=instance,
                phone=phone,
                resident=resident,
                session=session,
                message=text,
                on_purchase=lambda: _handle_product_search(
                    tenant_id, instance, phone, resident, session, text,
                ),
            )

    return False


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
    if session.state == ChatSession.State.AWAITING_PRODUCT_SELECTION:
        return _handle_product_selection(
            tenant_id, instance, phone, resident, session, text, interactive_id,
        )
    if session.state == ChatSession.State.AWAITING_QUANTITY:
        return _handle_quantity(instance, phone, resident, session, text)
    if session.state == ChatSession.State.AWAITING_LOOP_DECISION:
        return _handle_loop_decision(instance, phone, resident, session, interactive_id, text)
    if session.state == ChatSession.State.AWAITING_PHOTO:
        return _handle_photo(instance, phone, resident, session, event)
    if session.state == ChatSession.State.ACTIVE_BOT and interactive_id:
        if interactive_id.startswith(PROD_ID_PREFIX):
            return _handle_product_selection(
                tenant_id, instance, phone, resident, session, text, interactive_id,
            )
    return False


def _handle_product_search(
    tenant_id: int,
    instance: WhatsappInstance,
    phone: str,
    resident: Resident,
    session: ChatSession,
    text: str,
) -> bool:
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
        cart = get_or_create_open_cart(resident)
        session.active_cart = cart
        session.state = ChatSession.State.AWAITING_PRODUCT_SELECTION
        session.pending_product = None
        session.temporary_name = ""
        session.save(
            update_fields=[
                "active_cart",
                "state",
                "pending_product",
                "temporary_name",
                "updated_at",
            ],
        )
        send_whatsapp_reply(instance, phone, ASK_PRODUCT_MESSAGE)
        return True

    products = search_active_products(tenant_id, term)
    if not products:
        send_whatsapp_reply(
            instance,
            phone,
            f'Não encontrei "{term}" no catálogo. Tente outro nome de produto.',
        )
        return True

    cart = get_or_create_open_cart(resident)
    session.active_cart = cart
    session.state = ChatSession.State.AWAITING_PRODUCT_SELECTION
    session.pending_product = None
    _save_product_skus(session, products)
    session.save(update_fields=["active_cart", "state", "pending_product", "updated_at"])

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
    if not row_id and text.strip() and not _load_products_from_session(session, tenant_id):
        return _handle_product_search(
            tenant_id, instance, phone, resident, session, text.strip(),
        )

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
        session.state = ChatSession.State.ACTIVE_BOT
        session.save(update_fields=["state", "updated_at"])
        return True

    cart = session.active_cart or get_or_create_open_cart(resident)
    session.active_cart = cart
    item, _ = CartItem.objects.update_or_create(
        cart=cart,
        product=product,
        defaults={
            "quantity": 0,
            "unit_price": product.price,
        },
    )
    session.pending_product = product
    session.state = ChatSession.State.AWAITING_QUANTITY
    session.save(
        update_fields=["active_cart", "pending_product", "state", "updated_at"],
    )

    send_whatsapp_reply(
        instance,
        phone,
        f"Perfeito! Quantas unidades de {product.name} você vai levar? (Digite apenas o número)",
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
        send_whatsapp_reply(instance, phone, "Digite apenas um número inteiro, ex.: 2")
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
        session.state = ChatSession.State.ACTIVE_BOT
        session.save(update_fields=["state", "updated_at"])
        return True

    item = CartItem.objects.filter(cart=cart, product=product).first()
    if not item:
        send_whatsapp_reply(instance, phone, "Item não encontrado. Comece uma nova busca.")
        session.state = ChatSession.State.ACTIVE_BOT
        session.save(update_fields=["state", "updated_at"])
        return True

    item.quantity = qty
    item.save(update_fields=["quantity"])
    cart.recalculate_total()
    subtotal = item.subtotal

    session.state = ChatSession.State.AWAITING_LOOP_DECISION
    session.pending_product = None
    session.save(update_fields=["state", "pending_product", "updated_at"])

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
        session.state = ChatSession.State.ACTIVE_BOT
        session.pending_product = None
        session.save(update_fields=["state", "pending_product", "updated_at"])
        send_whatsapp_reply(instance, phone, "O que mais deseja levar? Digite o nome do produto.")
        return True

    if choice == CART_CHECKOUT:
        cart = session.active_cart
        if not cart:
            cart = get_or_create_open_cart(resident)
            session.active_cart = cart
        cart.recalculate_total()
        if cart.total_value <= Decimal("0"):
            send_whatsapp_reply(instance, phone, "Seu carrinho está vazio. Adicione itens primeiro.")
            return True

        cart.status = Cart.Status.AWAITING_PHOTO
        cart.save(update_fields=["status", "updated_at"])
        session.state = ChatSession.State.AWAITING_PHOTO
        session.save(update_fields=["state", "updated_at"])

        send_whatsapp_reply(
            instance,
            phone,
            "Para garantir a segurança do nosso mercado de condomínio, por favor, "
            "tire uma foto nítida de todos os produtos que você está levando "
            "antes de prosseguirmos com o pagamento.",
        )
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
        # Evolution pode enviar evento vazio antes da mídia; não irritar o morador.
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

    session.state = ChatSession.State.ACTIVE_BOT
    session.save(update_fields=["state", "updated_at"])

    send_whatsapp_reply(
        instance,
        phone,
        f"Pix Copia e Cola:\n\n{pix_code}\n\n"
        f"Total: {_format_brl(cart.total_value)}",
    )
    return True

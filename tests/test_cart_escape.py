from decimal import Decimal
from unittest import mock

import pytest

from apps.integrations.services.webhook_handlers import handle_evolution_webhook
from apps.integrations.services.webhook_parser import EvolutionWebhookEvent
from apps.residents.models import ChatSession
from apps.sales.models import Cart
from apps.sales.services.cart_escape import (
    GLOBAL_ESCAPE_ACK_MESSAGE,
    is_global_escape_message,
    should_escape_product_search_for_intent,
)
from apps.sales.services.cart_flow import process_cart_flow
from apps.sales.services.whatsapp_interactive import CART_CHECKOUT
from apps.tenants.context import tenant_scope
from tests.factories import (
    CartFactory,
    CartItemFactory,
    ChatSessionFactory,
    ProductFactory,
    ResidentFactory,
    TenantFactory,
    WhatsappInstanceFactory,
)


def test_should_escape_product_search_for_long_problem_text():
    text = (
        "Não estou procurando produto, enviei uma imagem que a geladeira esta quebrada"
    )
    assert should_escape_product_search_for_intent(text) is True
    assert should_escape_product_search_for_intent("A Luz de entrada esta queimada") is True
    assert should_escape_product_search_for_intent("Geladeira desligada") is True
    assert should_escape_product_search_for_intent("Cocada") is False
    assert should_escape_product_search_for_intent("Doritos 140g") is False


def _event_text(text: str, phone: str = "5511999887766") -> EvolutionWebhookEvent:
    return EvolutionWebhookEvent(
        event_type="MESSAGE",
        instance_key="inst",
        connection_state="",
        remote_jid=f"{phone}@s.whatsapp.net",
        message_id="msg-escape",
        from_me=False,
        message_text=text,
        message_kind="text",
    )


@pytest.mark.django_db
def test_global_escape_cancele_essa_compra_via_cart_flow():
    tenant = TenantFactory()
    instance = WhatsappInstanceFactory(tenant=tenant)
    resident = ResidentFactory(tenant=tenant, phone_number="5511999887766")
    cart = CartFactory(
        tenant=tenant,
        resident=resident,
        status=Cart.Status.OPEN,
        total_value=Decimal("10.00"),
    )
    session = ChatSessionFactory(
        tenant=tenant,
        phone_number=resident.phone_number,
        state=ChatSession.State.CART_REVIEW,
        active_cart=cart,
    )

    with mock.patch("apps.sales.services.cart_escape.send_whatsapp_reply") as send:
        with tenant_scope(tenant.id):
            handled = process_cart_flow(
                tenant.id,
                instance,
                resident.phone_number,
                _event_text("cancele essa compra"),
            )

    assert handled is True
    cart.refresh_from_db()
    session.refresh_from_db()
    assert cart.status == Cart.Status.CANCELLED
    assert session.state == ChatSession.State.IDLE
    assert session.active_cart_id is None
    assert GLOBAL_ESCAPE_ACK_MESSAGE in send.call_args[0][2]


@pytest.mark.parametrize("text", ["cancela", "nada", "nao quero nada", "esquece"])
def test_global_escape_cancela_and_nada(text):
    assert is_global_escape_message(text) is True


@pytest.mark.django_db
def test_product_search_none_with_nada_triggers_escape():
    tenant = TenantFactory()
    instance = WhatsappInstanceFactory(tenant=tenant)
    resident = ResidentFactory(tenant=tenant, phone_number="5511999887766")
    session = ChatSessionFactory(
        tenant=tenant,
        phone_number=resident.phone_number,
        state=ChatSession.State.PRODUCT_SEARCH,
    )

    with (
        mock.patch(
            "apps.sales.services.cart_flow.extract_product_term",
            return_value="NONE",
        ),
        mock.patch("apps.sales.services.cart_escape.send_whatsapp_reply") as send,
    ):
        with tenant_scope(tenant.id):
            handled = process_cart_flow(
                tenant.id,
                instance,
                resident.phone_number,
                _event_text("nada"),
            )

    assert handled is True
    session.refresh_from_db()
    assert session.state == ChatSession.State.IDLE
    assert GLOBAL_ESCAPE_ACK_MESSAGE in send.call_args[0][2]


@pytest.mark.django_db
def test_global_escape_via_webhook_handler_before_cart_state():
    tenant = TenantFactory()
    instance = WhatsappInstanceFactory(tenant=tenant)
    resident = ResidentFactory(tenant=tenant, phone_number="5511999887766")
    cart = CartFactory(
        tenant=tenant,
        resident=resident,
        status=Cart.Status.AWAITING_PHOTO,
    )
    ChatSessionFactory(
        tenant=tenant,
        phone_number=resident.phone_number,
        state=ChatSession.State.AWAITING_PHOTO,
        active_cart=cart,
    )

    event = _event_text("cancelar atendimento", resident.phone_number)

    with (
        mock.patch("apps.integrations.services.webhook_handlers.handle_global_escape") as escape,
        mock.patch("apps.integrations.services.webhook_handlers.process_cart_flow") as cart_flow,
    ):
        escape.return_value = True
        handle_evolution_webhook(event, instance)

    escape.assert_called_once()
    cart_flow.assert_not_called()


@pytest.mark.django_db
def test_loop_decision_finalizar_text_goes_to_photo():
    tenant = TenantFactory()
    instance = WhatsappInstanceFactory(tenant=tenant)
    resident = ResidentFactory(tenant=tenant, phone_number="5511999887766")
    product = ProductFactory(tenant=tenant, price=Decimal("12.00"))
    cart = CartFactory(
        tenant=tenant,
        resident=resident,
        total_value=Decimal("12.00"),
    )
    CartItemFactory(cart=cart, product=product, quantity=1, unit_price=product.price)
    session = ChatSessionFactory(
        tenant=tenant,
        phone_number=resident.phone_number,
        state=ChatSession.State.CART_REVIEW,
        active_cart=cart,
    )

    with mock.patch("apps.sales.services.cart_flow.send_whatsapp_reply") as send:
        with tenant_scope(tenant.id):
            handled = process_cart_flow(
                tenant.id,
                instance,
                resident.phone_number,
                _event_text("Quero finalizar a compra"),
            )

    assert handled is True
    session.refresh_from_db()
    cart.refresh_from_db()
    assert session.state == ChatSession.State.AWAITING_PHOTO
    assert cart.status == Cart.Status.AWAITING_PHOTO
    assert "foto" in send.call_args[0][2].lower()


@pytest.mark.django_db
def test_loop_decision_adicionar_mais_text_returns_active_bot():
    tenant = TenantFactory()
    instance = WhatsappInstanceFactory(tenant=tenant)
    resident = ResidentFactory(tenant=tenant, phone_number="5511999887766")
    cart = CartFactory(tenant=tenant, resident=resident, total_value=Decimal("5.00"))
    session = ChatSessionFactory(
        tenant=tenant,
        phone_number=resident.phone_number,
        state=ChatSession.State.CART_REVIEW,
        active_cart=cart,
    )

    with mock.patch("apps.sales.services.cart_flow.send_whatsapp_reply") as send:
        with tenant_scope(tenant.id):
            handled = process_cart_flow(
                tenant.id,
                instance,
                resident.phone_number,
                _event_text("continuar comprando mais itens"),
            )

    assert handled is True
    session.refresh_from_db()
    assert session.state == ChatSession.State.PRODUCT_SEARCH
    assert "nome do produto" in send.call_args[0][2].lower()


@pytest.mark.django_db
def test_loop_decision_unknown_text_shows_friendly_fallback():
    tenant = TenantFactory()
    instance = WhatsappInstanceFactory(tenant=tenant)
    resident = ResidentFactory(tenant=tenant, phone_number="5511999887766")
    cart = CartFactory(tenant=tenant, resident=resident)
    ChatSessionFactory(
        tenant=tenant,
        phone_number=resident.phone_number,
        state=ChatSession.State.CART_REVIEW,
        active_cart=cart,
    )

    with mock.patch("apps.sales.services.cart_flow.send_whatsapp_reply") as send:
        with tenant_scope(tenant.id):
            handled = process_cart_flow(
                tenant.id,
                instance,
                resident.phone_number,
                _event_text("banana"),
            )

    assert handled is True
    assert "Finalizar" in send.call_args[0][2]
    assert "Cancelar" in send.call_args[0][2]


@pytest.mark.parametrize(
    "text,expected",
    [
        ("finalizar", CART_CHECKOUT),
        ("2", CART_CHECKOUT),
        ("adicionar mais coisas", "cart:add_more"),
    ],
)
def test_resolve_loop_choice_from_text(text, expected):
    from apps.sales.services.cart_escape import resolve_loop_choice_from_text

    assert resolve_loop_choice_from_text(text) == expected

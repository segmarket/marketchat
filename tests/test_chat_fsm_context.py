from decimal import Decimal
from unittest import mock

import pytest

from apps.integrations.services.webhook_parser import EvolutionWebhookEvent
from apps.products.models import Product
from apps.residents.models import ChatSession
from apps.sales.services.cart_flow import process_cart_flow
from apps.sales.services.product_search import ASK_PRODUCT_MESSAGE
from apps.tenants.context import tenant_scope
from tests.factories import (
    CartFactory,
    CartItemFactory,
    ProductFactory,
    ResidentFactory,
    TenantFactory,
    WhatsappInstanceFactory,
    ChatSessionFactory,
)


def _event_text(text: str, *, interactive_id: str = "") -> EvolutionWebhookEvent:
    return EvolutionWebhookEvent(
        event_type="MESSAGES_UPSERT",
        instance_key="test",
        remote_jid="5511999887766@s.whatsapp.net",
        message_text=text,
        message_id="msg-1",
        from_me=False,
        message_kind="text",
        interactive_id=interactive_id,
        raw_message={},
        connection_state="",
    )


@pytest.mark.django_db
def test_purchase_with_last_discussed_skips_ask_product():
    tenant = TenantFactory()
    instance = WhatsappInstanceFactory(tenant=tenant)
    resident = ResidentFactory(tenant=tenant, phone_number="5511999887766")
    product = ProductFactory(tenant=tenant, name="Coca-Cola 2L", sku="COCA-2L")
    session = ChatSessionFactory(
        tenant=tenant,
        phone_number=resident.phone_number,
        state=ChatSession.State.IDLE,
        last_discussed_product=product,
    )

    with (
        mock.patch("apps.sales.services.cart_flow.send_whatsapp_reply"),
        mock.patch("apps.sales.services.cart_flow.send_product_list") as send_list,
        mock.patch(
            "apps.sales.services.active_bot_router.classify_user_intent",
            return_value="PURCHASE",
        ),
        mock.patch(
            "apps.sales.services.cart_flow.extract_product_term",
            return_value="NONE",
        ),
        mock.patch(
            "apps.sales.services.cart_flow.search_active_products",
            return_value=[product],
        ),
    ):
        with tenant_scope(tenant.id):
            handled = process_cart_flow(
                tenant.id,
                instance,
                resident.phone_number,
                _event_text("Quero comprar"),
            )

    assert handled is True
    session.refresh_from_db()
    assert session.state == ChatSession.State.PRODUCT_SEARCH
    send_list.assert_called_once()
    assert ASK_PRODUCT_MESSAGE not in str(send_list.call_args_list)


@pytest.mark.django_db
def test_finalize_in_idle_with_active_cart_goes_to_photo():
    tenant = TenantFactory()
    instance = WhatsappInstanceFactory(tenant=tenant)
    resident = ResidentFactory(tenant=tenant, phone_number="5511999887766")
    product = ProductFactory(tenant=tenant, price=Decimal("10.00"))
    cart = CartFactory(tenant=tenant, resident=resident, total_value=Decimal("10.00"))
    CartItemFactory(cart=cart, product=product, quantity=1, unit_price=product.price)
    session = ChatSessionFactory(
        tenant=tenant,
        phone_number=resident.phone_number,
        state=ChatSession.State.IDLE,
        active_cart=cart,
    )

    with mock.patch("apps.sales.services.cart_escape.send_whatsapp_reply") as send:
        with tenant_scope(tenant.id):
            handled = process_cart_flow(
                tenant.id,
                instance,
                resident.phone_number,
                _event_text("Finalizar"),
            )

    assert handled is True
    session.refresh_from_db()
    cart.refresh_from_db()
    assert session.state == ChatSession.State.AWAITING_PHOTO
    assert cart.status == cart.Status.AWAITING_PHOTO
    assert "foto" in send.call_args[0][2].lower()


@pytest.mark.django_db
def test_global_escape_clears_last_discussed_product():
    tenant = TenantFactory()
    instance = WhatsappInstanceFactory(tenant=tenant)
    resident = ResidentFactory(tenant=tenant, phone_number="5511999887766")
    product = ProductFactory(tenant=tenant)
    session = ChatSessionFactory(
        tenant=tenant,
        phone_number=resident.phone_number,
        state=ChatSession.State.PRODUCT_SEARCH,
        last_discussed_product=product,
        active_cart=CartFactory(tenant=tenant, resident=resident),
    )

    with mock.patch("apps.sales.services.cart_escape.send_whatsapp_reply"):
        with tenant_scope(tenant.id):
            from apps.sales.services.cart_escape import handle_global_escape

            assert handle_global_escape(
                instance=instance,
                phone=resident.phone_number,
                resident=resident,
                text="Cancelar",
            )

    session.refresh_from_db()
    assert session.state == ChatSession.State.IDLE
    assert session.last_discussed_product_id is None

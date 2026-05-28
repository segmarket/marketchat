from decimal import Decimal
from unittest import mock

import pytest

from apps.residents.models import ChatSession
from apps.sales.services.cart_flow import process_cart_flow
from apps.sales.services.product_selection import is_product_selection_escape
from apps.tenants.context import tenant_scope
from tests.factories import (
    CartFactory,
    ChatSessionFactory,
    ProductFactory,
    ResidentFactory,
    TenantFactory,
    WhatsappInstanceFactory,
)
from tests.test_cart_flow import _event_text


@pytest.mark.parametrize(
    "text",
    [
        "Não é esse produto",
        "nenhum",
        "errei",
        "cancela",
    ],
)
def test_is_product_selection_escape(text):
    assert is_product_selection_escape(text) is True


@pytest.mark.django_db
def test_escape_from_product_selection():
    tenant = TenantFactory()
    instance = WhatsappInstanceFactory(tenant=tenant)
    resident = ResidentFactory(tenant=tenant, phone_number="5511999887766")
    coca = ProductFactory(
        tenant=tenant,
        sku="COCA-ZERO",
        name="Coca Cola Lata Zero 350ml",
        price=Decimal("6.00"),
    )
    ProductFactory(tenant=tenant, sku="PEPSI", name="Pepsi 350ml")
    session = ChatSessionFactory(
        tenant=tenant,
        phone_number=resident.phone_number,
        state=ChatSession.State.PRODUCT_SEARCH,
        temporary_name=f"{coca.sku},PEPSI",
    )

    with (
        mock.patch("apps.sales.services.cart_flow.send_whatsapp_reply") as send,
        mock.patch("apps.sales.services.cart_flow.send_product_list") as send_list,
        mock.patch("apps.sales.services.cart_flow.extract_product_term") as extract,
    ):
        with tenant_scope(tenant.id):
            handled = process_cart_flow(
                tenant.id,
                instance,
                resident.phone_number,
                _event_text("Não é esse produto", resident.phone_number),
            )

    assert handled is True
    session.refresh_from_db()
    assert session.state == ChatSession.State.PRODUCT_SEARCH
    assert session.temporary_name == ""
    send_list.assert_not_called()
    extract.assert_not_called()
    body = send.call_args[0][2]
    assert "Vamos tentar de novo" in body


@pytest.mark.django_db
def test_add_more_clears_list_and_searches_new_product():
    tenant = TenantFactory()
    instance = WhatsappInstanceFactory(tenant=tenant)
    resident = ResidentFactory(tenant=tenant, phone_number="5511999887766")
    cart = CartFactory(tenant=tenant, resident=resident, total_value=Decimal("6.00"))
    coca = ProductFactory(
        tenant=tenant,
        sku="COCA-ZERO",
        name="Coca Cola Lata Zero 350ml",
        price=Decimal("6.00"),
    )
    queijo = ProductFactory(
        tenant=tenant,
        sku="QUEIJO-01",
        name="Queijo Minas 500g",
        price=Decimal("18.00"),
    )
    session = ChatSessionFactory(
        tenant=tenant,
        phone_number=resident.phone_number,
        state=ChatSession.State.CART_REVIEW,
        active_cart=cart,
        temporary_name=coca.sku,
    )
    session.last_discussed_product = coca
    session.save(update_fields=["last_discussed_product", "updated_at"])

    with (
        mock.patch("apps.sales.services.cart_flow.send_whatsapp_reply"),
        mock.patch("apps.sales.services.cart_flow.send_product_list") as send_list,
        mock.patch(
            "apps.sales.services.cart_flow.extract_product_term",
            return_value="Quejo",
        ),
    ):
        with tenant_scope(tenant.id):
            from apps.sales.services.whatsapp_interactive import CART_ADD_MORE
            from tests.test_cart_flow import _event_interactive

            process_cart_flow(
                tenant.id,
                instance,
                resident.phone_number,
                _event_interactive(CART_ADD_MORE, resident.phone_number),
            )
            session.refresh_from_db()
            assert session.state == ChatSession.State.PRODUCT_SEARCH
            assert session.temporary_name == ""
            assert session.last_discussed_product_id is None

            handled = process_cart_flow(
                tenant.id,
                instance,
                resident.phone_number,
                _event_text("Quejo", resident.phone_number),
            )

    assert handled is True
    send_list.assert_called_once()
    products_sent = send_list.call_args[0][2]
    assert queijo in products_sent
    assert coca not in products_sent

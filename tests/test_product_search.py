from decimal import Decimal
from unittest import mock

import pytest

from apps.residents.models import ChatSession
from apps.sales.services.cart_flow import process_cart_flow
from apps.sales.services.intent_gatekeeper import PURCHASE
from apps.sales.services.product_search import (
    build_product_name_q,
    is_product_term_none,
    search_active_products,
)
from apps.tenants.context import tenant_scope
from tests.factories import (
    ChatSessionFactory,
    ProductFactory,
    ResidentFactory,
    TenantFactory,
    WhatsappInstanceFactory,
)


@pytest.mark.django_db
def test_split_word_search_coca_zero_finds_product():
    tenant = TenantFactory()
    product = ProductFactory(
        tenant=tenant,
        sku="COCA-ZERO",
        name="Coca Cola Lata Zero 350ml",
    )
    ProductFactory(tenant=tenant, sku="PEPSI", name="Pepsi 350ml")

    results = search_active_products(tenant.id, "Coca Zero")

    assert list(results) == [product]


@pytest.mark.django_db
def test_build_product_name_q_ignores_single_letter_tokens():
    tenant = TenantFactory()
    ProductFactory(tenant=tenant, name="Coca Cola Lata Zero 350ml")

    from apps.products.models import Product

    qs = Product.objects.filter(
        tenant_id=tenant.id,
        status=Product.Status.ACTIVE,
    ).filter(build_product_name_q("C o c a Zero"))

    assert qs.count() == 1


@pytest.mark.parametrize(
    "term",
    ["NONE", " none ", "NONE\n", '"NONE"'],
)
def test_is_product_term_none(term):
    assert is_product_term_none(term) is True


@pytest.mark.django_db
def test_quero_comprar_without_product_asks_instead_of_not_found():
    from tests.test_cart_flow import _event_text

    tenant = TenantFactory()
    instance = WhatsappInstanceFactory(tenant=tenant)
    resident = ResidentFactory(tenant=tenant, phone_number="5511999887766")
    session = ChatSessionFactory(
        tenant=tenant,
        phone_number=resident.phone_number,
        state=ChatSession.State.IDLE,
    )

    with (
        mock.patch(
            "apps.sales.services.active_bot_router.classify_user_intent",
            return_value=PURCHASE,
        ),
        mock.patch(
            "apps.sales.services.cart_flow.extract_product_term",
            return_value="NONE",
        ),
        mock.patch("apps.sales.services.cart_flow.send_product_list") as send_list,
        mock.patch("apps.sales.services.cart_flow.send_whatsapp_reply") as send_reply,
    ):
        with tenant_scope(tenant.id):
            handled = process_cart_flow(
                tenant.id,
                instance,
                resident.phone_number,
                _event_text("quero comprar", resident.phone_number),
            )

    assert handled is True
    session.refresh_from_db()
    assert session.state == ChatSession.State.PRODUCT_SEARCH
    assert session.active_cart_id is not None
    send_list.assert_not_called()
    reply = send_reply.call_args[0][2]
    assert "O que você deseja comprar" in reply
    assert "não encontrei" not in reply.lower()


@pytest.mark.django_db
def test_product_search_after_none_finds_with_split_words():
    from tests.test_cart_flow import _event_text

    tenant = TenantFactory()
    instance = WhatsappInstanceFactory(tenant=tenant)
    resident = ResidentFactory(tenant=tenant, phone_number="5511999887766")
    ProductFactory(
        tenant=tenant,
        sku="COCA-ZERO",
        name="Coca Cola Lata Zero 350ml",
        price=Decimal("6.00"),
    )
    session = ChatSessionFactory(
        tenant=tenant,
        phone_number=resident.phone_number,
        state=ChatSession.State.PRODUCT_SEARCH,
        temporary_name="",
    )

    with (
        mock.patch(
            "apps.sales.services.cart_flow.extract_product_term",
            return_value="Coca Zero",
        ),
        mock.patch("apps.sales.services.cart_flow.send_product_list") as send_list,
    ):
        with tenant_scope(tenant.id):
            handled = process_cart_flow(
                tenant.id,
                instance,
                resident.phone_number,
                _event_text("Coca Zero", resident.phone_number),
            )

    assert handled is True
    send_list.assert_called_once()
    products_sent = send_list.call_args[0][2]
    assert any("Zero" in p.name for p in products_sent)

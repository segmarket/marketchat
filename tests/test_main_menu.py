from unittest import mock

import pytest

from apps.residents.models import ChatSession
from apps.sales.services.active_bot_router import route_idle_message
from apps.sales.services.cart_flow import process_cart_flow
from apps.sales.services.main_menu import parse_main_menu_choice
from apps.sales.services.product_search import MAIN_MENU_PURCHASE_PROMPT
from apps.tenants.context import tenant_scope
from tests.factories import (
    ChatSessionFactory,
    ResidentFactory,
    TenantFactory,
    WhatsappInstanceFactory,
)
from tests.test_cart_escape import _event_text


@pytest.mark.parametrize(
    "text,expected",
    [
        ("1", 1),
        ("1️⃣", 1),
        ("opcao 2", 2),
        ("opção 3", 3),
        ("um", 1),
        ("quatro", 4),
        ("banana", None),
    ],
)
def test_parse_main_menu_choice(text, expected):
    assert parse_main_menu_choice(text) == expected


@pytest.mark.django_db
def test_greeting_transitions_to_main_menu():
    from apps.chatbot.services.chat_context_cache import clear_context
    from tests.factories import MarketFactory

    tenant = TenantFactory()
    market = MarketFactory(tenant=tenant)
    resident = ResidentFactory(tenant=tenant, market=market, name="Maria Silva")
    instance = WhatsappInstanceFactory(tenant=tenant)
    session = ChatSessionFactory(
        tenant=tenant,
        phone_number=resident.phone_number,
        state=ChatSession.State.IDLE,
    )
    clear_context(tenant.id, resident.phone_number)

    send_mock = mock.Mock()
    purchase_mock = mock.Mock(return_value=False)

    with (
        mock.patch(
            "apps.sales.services.active_bot_router.classify_user_intent",
            return_value="GREETING",
        ),
        mock.patch(
            "apps.sales.services.main_menu.send_whatsapp_reply",
            send_mock,
        ),
    ):
        route_idle_message(
            tenant_id=tenant.id,
            instance=instance,
            phone=resident.phone_number,
            resident=resident,
            session=session,
            message="Bom dia",
            on_purchase=purchase_mock,
        )

    purchase_mock.assert_not_called()
    session.refresh_from_db()
    assert session.state == ChatSession.State.AWAITING_MAIN_MENU

    body = send_mock.call_args[0][2]
    assert "Maria" in body
    assert "Fazer uma compra" in body
    assert "O que você precisa" not in body


@pytest.mark.django_db
def test_main_menu_option_1_starts_product_search():
    tenant = TenantFactory()
    instance = WhatsappInstanceFactory(tenant=tenant)
    resident = ResidentFactory(tenant=tenant, phone_number="5511999887766")
    session = ChatSessionFactory(
        tenant=tenant,
        phone_number=resident.phone_number,
        state=ChatSession.State.AWAITING_MAIN_MENU,
    )

    with mock.patch("apps.sales.services.main_menu.send_whatsapp_reply") as send:
        with tenant_scope(tenant.id):
            handled = process_cart_flow(
                tenant.id,
                instance,
                resident.phone_number,
                _event_text("1"),
            )

    assert handled is True
    session.refresh_from_db()
    assert session.state == ChatSession.State.PRODUCT_SEARCH
    assert session.active_cart_id is not None
    assert MAIN_MENU_PURCHASE_PROMPT in send.call_args[0][2]


@pytest.mark.django_db
def test_main_menu_option_4_resets_session():
    tenant = TenantFactory()
    instance = WhatsappInstanceFactory(tenant=tenant)
    resident = ResidentFactory(tenant=tenant, phone_number="5511999887766")
    session = ChatSessionFactory(
        tenant=tenant,
        phone_number=resident.phone_number,
        state=ChatSession.State.AWAITING_MAIN_MENU,
    )

    with mock.patch("apps.sales.services.main_menu.send_whatsapp_reply") as send:
        with tenant_scope(tenant.id):
            handled = process_cart_flow(
                tenant.id,
                instance,
                resident.phone_number,
                _event_text("4"),
            )

    assert handled is True
    session.refresh_from_db()
    assert session.state == ChatSession.State.IDLE
    assert "Até mais" in send.call_args[0][2]

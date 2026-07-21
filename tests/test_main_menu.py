from unittest import mock

import pytest

from apps.notifications.models import Notification
from apps.residents.models import ChatSession
from apps.sales.services.active_bot_router import route_idle_message
from apps.sales.services.cart_flow import process_cart_flow
from apps.sales.services.main_menu import parse_main_menu_choice
from apps.sales.services.product_search import MAIN_MENU_PURCHASE_PROMPT
from apps.sales.services.whatsapp_interactive import (
    MENU_OTHER,
    MENU_PURCHASE,
    MENU_STOCK,
    MENU_SUGGEST,
    MENU_UNCATALOGUED,
)
from apps.tenants.context import tenant_scope
from tests.factories import (
    ChatSessionFactory,
    MarketFactory,
    ResidentFactory,
    TenantFactory,
    WhatsappInstanceFactory,
)
from tests.test_cart_escape import _event_text
from tests.test_cart_flow import _event_interactive


@pytest.mark.parametrize(
    "text,expected",
    [
        ("1", MENU_PURCHASE),
        ("1️⃣", MENU_PURCHASE),
        ("opcao 2", MENU_SUGGEST),
        ("opção 3", MENU_STOCK),
        ("um", MENU_PURCHASE),
        ("dez", MENU_OTHER),
        ("10", MENU_OTHER),
        ("banana", None),
    ],
)
def test_parse_main_menu_choice(text, expected):
    assert parse_main_menu_choice(text) == expected


def test_parse_main_menu_interactive_id():
    assert parse_main_menu_choice("", interactive_id=MENU_SUGGEST) == MENU_SUGGEST
    assert parse_main_menu_choice("1", interactive_id=MENU_STOCK) == MENU_STOCK
    assert parse_main_menu_choice("", interactive_id="menu:unknown") is None


@pytest.mark.django_db
def test_greeting_sends_interactive_list():
    from apps.chatbot.services.chat_context_cache import clear_context

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

    purchase_mock = mock.Mock(return_value=False)

    with (
        mock.patch(
            "apps.sales.services.active_bot_router.classify_user_intent",
            return_value="GREETING",
        ),
        mock.patch(
            "apps.sales.services.main_menu.send_main_menu_list",
            return_value=True,
        ) as send_list,
        mock.patch(
            "apps.sales.services.main_menu.log_outbound",
        ) as log_out,
        mock.patch(
            "apps.sales.services.main_menu.send_whatsapp_reply",
        ) as send_text,
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
    send_list.assert_called_once()
    send_text.assert_not_called()
    logged = log_out.call_args.kwargs["message_text"]
    assert "Maria" in logged
    assert "Fazer uma compra" in logged
    assert "Sugestão de produto" in logged


@pytest.mark.django_db
def test_greeting_falls_back_to_text_menu_when_list_fails():
    from apps.chatbot.services.chat_context_cache import clear_context

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

    with (
        mock.patch(
            "apps.sales.services.active_bot_router.classify_user_intent",
            return_value="GREETING",
        ),
        mock.patch(
            "apps.sales.services.main_menu.send_main_menu_list",
            return_value=False,
        ),
        mock.patch(
            "apps.sales.services.main_menu.send_whatsapp_reply",
        ) as send_text,
    ):
        route_idle_message(
            tenant_id=tenant.id,
            instance=instance,
            phone=resident.phone_number,
            resident=resident,
            session=session,
            message="Bom dia",
            on_purchase=mock.Mock(return_value=False),
        )

    body = send_text.call_args[0][2]
    assert "Fazer uma compra" in body
    assert "1 —" in body or "1 —" in body


@pytest.mark.django_db
def test_main_menu_ignores_repeated_greeting_without_reminder():
    tenant = TenantFactory()
    instance = WhatsappInstanceFactory(tenant=tenant)
    resident = ResidentFactory(tenant=tenant, phone_number="5511999887766")
    ChatSessionFactory(
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
                _event_text("Oi Bom dia"),
            )

    assert handled is True
    send.assert_not_called()


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
def test_main_menu_interactive_suggest_awaits_product():
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
                _event_interactive(MENU_SUGGEST, resident.phone_number),
            )

    assert handled is True
    session.refresh_from_db()
    assert session.state == ChatSession.State.AWAITING_PRODUCT_SUGGESTION
    assert "sugerir" in send.call_args[0][2].lower()


@pytest.mark.django_db
def test_main_menu_option_4_uncatalogued_goes_idle():
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
    assert parse_main_menu_choice("4") == MENU_UNCATALOGUED
    assert "cadastro" in send.call_args[0][2].lower() or "preço" in send.call_args[0][2].lower()


@pytest.mark.django_db
def test_product_suggestion_notifies_owner_and_panel():
    tenant = TenantFactory(phone="5511888777666")
    market = MarketFactory(tenant=tenant, name="Torre A")
    instance = WhatsappInstanceFactory(tenant=tenant)
    resident = ResidentFactory(
        tenant=tenant,
        market=market,
        phone_number="5511999887766",
        name="João",
    )
    session = ChatSessionFactory(
        tenant=tenant,
        phone_number=resident.phone_number,
        state=ChatSession.State.AWAITING_PRODUCT_SUGGESTION,
    )

    with (
        mock.patch(
            "apps.sales.services.product_suggestion_handler.extract_product_term",
            return_value="Doritos",
        ),
        mock.patch(
            "apps.sales.services.product_suggestion_handler.send_whatsapp_reply",
        ) as send_resident,
        mock.patch(
            "apps.sales.services.owner_alert.send_whatsapp_reply",
        ) as send_owner,
    ):
        with tenant_scope(tenant.id):
            handled = process_cart_flow(
                tenant.id,
                instance,
                resident.phone_number,
                _event_text("Queria que tivesse Doritos"),
            )

    assert handled is True
    session.refresh_from_db()
    assert session.state == ChatSession.State.IDLE
    assert "Doritos" in send_resident.call_args[0][2]
    assert "SUGESTÃO" in send_owner.call_args[0][2]
    note = Notification.all_objects.filter(
        tenant=tenant,
        intent_type="PRODUCT_SUGGESTION",
    ).first()
    assert note is not None
    assert note.severity == Notification.Severity.INFO
    assert "Doritos" in note.message

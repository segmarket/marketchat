from unittest import mock
from decimal import Decimal

import pytest

from apps.notifications.models import Notification
from apps.residents.models import ChatSession
from apps.sales.services.active_bot_router import route_idle_message
from apps.sales.services.cart_flow import process_cart_flow
from apps.sales.services.main_menu import parse_main_menu_choice
from apps.sales.services.whatsapp_interactive import (
    MENU_BILLING,
    MENU_OTHER,
    MENU_PAYMENT,
    MENU_UNCATALOGUED,
    SUPPORT_DETAILS_PROMPT,
    SUPPORT_WAITING_QUEUE_MESSAGE,
    UNREGISTERED_PRODUCT_NOT_FOUND_MESSAGE,
    UNREGISTERED_PRODUCT_SEARCH_PROMPT,
)
from apps.tenants.context import tenant_scope
from tests.factories import (
    ChatSessionFactory,
    MarketFactory,
    ProductFactory,
    ResidentFactory,
    TenantFactory,
    WhatsappInstanceFactory,
)
from tests.test_cart_escape import _event_text
from tests.test_cart_flow import _event_interactive


@pytest.mark.parametrize(
    "text,expected",
    [
        ("1", MENU_PAYMENT),
        ("1️⃣", MENU_PAYMENT),
        ("opcao 2", MENU_UNCATALOGUED),
        ("opção 3", MENU_BILLING),
        ("um", MENU_PAYMENT),
        ("sete", MENU_OTHER),
        ("7", MENU_OTHER),
        ("10", None),
        ("banana", None),
    ],
)
def test_parse_main_menu_choice(text, expected):
    assert parse_main_menu_choice(text) == expected


def test_parse_main_menu_interactive_id():
    assert parse_main_menu_choice("", interactive_id=MENU_UNCATALOGUED) == MENU_UNCATALOGUED
    assert parse_main_menu_choice("1", interactive_id=MENU_BILLING) == MENU_BILLING
    assert parse_main_menu_choice("", interactive_id="menu:unknown") is None
    assert parse_main_menu_choice("", interactive_id="menu:purchase") is None


@pytest.mark.django_db
def test_greeting_sends_text_menu():
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
    send_text.assert_called_once()
    body = send_text.call_args[0][2]
    assert "Maria" in body
    assert "Indisp. de pagamento ou queda sistema" in body
    assert "Produto sem cadastro" in body
    assert "Fazer uma compra" not in body
    assert 'Digite "sair"' in body or "Digite \"sair\"" in body
    assert "1 a 7" in body


@pytest.mark.django_db
def test_greeting_menu_does_not_call_evolution_list():
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
            "apps.integrations.services.evolution_client.EvolutionClient.send_list",
        ) as send_list,
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

    send_list.assert_not_called()
    body = send_text.call_args[0][2]
    assert "Indisp. de pagamento ou queda sistema" in body


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
def test_main_menu_option_1_fast_tracks_payment_backup_sale():
    tenant = TenantFactory()
    instance = WhatsappInstanceFactory(tenant=tenant)
    resident = ResidentFactory(tenant=tenant, phone_number="5511999887766")
    session = ChatSessionFactory(
        tenant=tenant,
        phone_number=resident.phone_number,
        state=ChatSession.State.AWAITING_MAIN_MENU,
    )

    from apps.sales.services.handlers.payment import SUPPORT_PAYMENT_BACKUP_SALE_MESSAGE

    with (
        mock.patch(
            "apps.sales.services.handlers.payment.notify_owner_support_issue",
        ),
        mock.patch(
            "apps.sales.services.handlers.payment.create_critical_panel_notification",
        ),
        mock.patch(
            "apps.sales.services.handlers.payment.send_whatsapp_reply",
        ) as send,
        mock.patch(
            "apps.sales.services.handlers.payment.append_assistant_message",
        ),
    ):
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
    assert session.temporary_name == ""
    assert send.call_args[0][2] == SUPPORT_PAYMENT_BACKUP_SALE_MESSAGE


@pytest.mark.django_db
def test_main_menu_option_2_starts_uncatalogued_product_search():
    tenant = TenantFactory()
    instance = WhatsappInstanceFactory(tenant=tenant)
    resident = ResidentFactory(tenant=tenant, phone_number="5511999887766")
    session = ChatSessionFactory(
        tenant=tenant,
        phone_number=resident.phone_number,
        state=ChatSession.State.AWAITING_MAIN_MENU,
    )

    with (
        mock.patch(
            "apps.sales.services.handlers.catalog.send_whatsapp_reply",
        ) as send,
        mock.patch(
            "apps.sales.services.cart_flow.route_idle_message",
        ) as route_idle,
    ):
        with tenant_scope(tenant.id):
            handled = process_cart_flow(
                tenant.id,
                instance,
                resident.phone_number,
                _event_text("2"),
            )

    assert handled is True
    session.refresh_from_db()
    assert session.state == ChatSession.State.SEARCHING_UNREGISTERED_PRODUCT
    assert session.temporary_name == ""
    assert session.state != ChatSession.State.AWAITING_SUPPORT_DETAILS
    assert send.call_args[0][2] == UNREGISTERED_PRODUCT_SEARCH_PROMPT
    route_idle.assert_not_called()


@pytest.mark.django_db
def test_main_menu_option_3_still_awaits_support_details():
    tenant = TenantFactory()
    instance = WhatsappInstanceFactory(tenant=tenant)
    resident = ResidentFactory(tenant=tenant, phone_number="5511999887766")
    session = ChatSessionFactory(
        tenant=tenant,
        phone_number=resident.phone_number,
        state=ChatSession.State.AWAITING_MAIN_MENU,
    )

    with mock.patch(
        "apps.sales.services.handlers._common.send_whatsapp_reply",
    ) as send:
        with tenant_scope(tenant.id):
            handled = process_cart_flow(
                tenant.id,
                instance,
                resident.phone_number,
                _event_text("3"),
            )

    assert handled is True
    session.refresh_from_db()
    assert session.state == ChatSession.State.AWAITING_SUPPORT_DETAILS
    assert session.temporary_name == MENU_BILLING
    assert send.call_args[0][2] == SUPPORT_DETAILS_PROMPT


@pytest.mark.django_db
def test_uncatalogued_search_found_enters_product_search_without_send_product_list():
    tenant = TenantFactory()
    instance = WhatsappInstanceFactory(tenant=tenant)
    resident = ResidentFactory(tenant=tenant, phone_number="5511999887766")
    session = ChatSessionFactory(
        tenant=tenant,
        phone_number=resident.phone_number,
        state=ChatSession.State.SEARCHING_UNREGISTERED_PRODUCT,
    )
    product = ProductFactory(
        tenant=tenant,
        sku="SKU-PACOCA",
        name="Paçoca",
        price=Decimal("2.50"),
    )

    with (
        mock.patch(
            "apps.sales.services.uncatalogued_product_flow.search_active_products",
            return_value=[product],
        ),
        mock.patch(
            "apps.sales.services.uncatalogued_product_flow.send_whatsapp_reply",
        ) as send,
        mock.patch(
            "apps.sales.services.cart_flow.send_product_list",
        ) as send_list,
    ):
        with tenant_scope(tenant.id):
            handled = process_cart_flow(
                tenant.id,
                instance,
                resident.phone_number,
                _event_text("paçoca"),
            )

    assert handled is True
    session.refresh_from_db()
    assert session.state == ChatSession.State.PRODUCT_SEARCH
    body = send.call_args[0][2]
    assert "Boa notícia" in body
    assert "Paçoca" in body
    assert "R$" in body
    send_list.assert_not_called()


@pytest.mark.django_db
def test_uncatalogued_search_not_found_queues_human_and_notifies_owner():
    tenant = TenantFactory()
    instance = WhatsappInstanceFactory(tenant=tenant)
    resident = ResidentFactory(tenant=tenant, phone_number="5511999887766")
    session = ChatSessionFactory(
        tenant=tenant,
        phone_number=resident.phone_number,
        state=ChatSession.State.SEARCHING_UNREGISTERED_PRODUCT,
        is_bot_active=False,
    )

    with (
        mock.patch(
            "apps.sales.services.uncatalogued_product_flow.search_active_products",
            return_value=[],
        ),
        mock.patch(
            "apps.sales.services.uncatalogued_product_flow.notify_owner_support_issue",
        ) as notify,
        mock.patch(
            "apps.sales.services.uncatalogued_product_flow.send_whatsapp_reply",
        ) as send,
    ):
        with tenant_scope(tenant.id):
            handled = process_cart_flow(
                tenant.id,
                instance,
                resident.phone_number,
                _event_text("produto inexistente"),
            )

    assert handled is True
    session.refresh_from_db()
    assert session.state == ChatSession.State.WAITING_FOR_HUMAN
    assert session.is_bot_active is True
    notify.assert_called_once()
    assert notify.call_args.kwargs["issue_label"] == "Produto sem cadastro"
    assert send.call_args[0][2] == UNREGISTERED_PRODUCT_NOT_FOUND_MESSAGE
    assert "Realmente esse produto" in send.call_args[0][2]


@pytest.mark.django_db
def test_main_menu_interactive_billing_awaits_details():
    tenant = TenantFactory()
    instance = WhatsappInstanceFactory(tenant=tenant)
    resident = ResidentFactory(tenant=tenant, phone_number="5511999887766")
    session = ChatSessionFactory(
        tenant=tenant,
        phone_number=resident.phone_number,
        state=ChatSession.State.AWAITING_MAIN_MENU,
    )

    with mock.patch(
        "apps.sales.services.handlers._common.send_whatsapp_reply",
    ) as send:
        with tenant_scope(tenant.id):
            handled = process_cart_flow(
                tenant.id,
                instance,
                resident.phone_number,
                _event_interactive(MENU_BILLING, resident.phone_number),
            )

    assert handled is True
    session.refresh_from_db()
    assert session.state == ChatSession.State.AWAITING_SUPPORT_DETAILS
    assert session.temporary_name == MENU_BILLING
    assert send.call_args[0][2] == SUPPORT_DETAILS_PROMPT


@pytest.mark.django_db
def test_support_details_payment_opens_backup_sale():
    tenant = TenantFactory()
    instance = WhatsappInstanceFactory(tenant=tenant)
    resident = ResidentFactory(tenant=tenant, phone_number="5511999887766")
    session = ChatSessionFactory(
        tenant=tenant,
        phone_number=resident.phone_number,
        state=ChatSession.State.AWAITING_SUPPORT_DETAILS,
        temporary_name=MENU_PAYMENT,
    )

    from apps.sales.services.handlers.payment import SUPPORT_PAYMENT_BACKUP_SALE_MESSAGE

    with (
        mock.patch(
            "apps.sales.services.handlers.payment.notify_owner_support_issue",
        ) as notify,
        mock.patch(
            "apps.sales.services.handlers.payment.create_critical_panel_notification",
        ),
        mock.patch(
            "apps.sales.services.handlers.payment.send_whatsapp_reply",
        ) as send,
        mock.patch(
            "apps.sales.services.handlers.payment.append_assistant_message",
        ),
    ):
        with tenant_scope(tenant.id):
            handled = process_cart_flow(
                tenant.id,
                instance,
                resident.phone_number,
                _event_text("Maquininha sem sinal"),
            )

    assert handled is True
    notify.assert_called_once()
    session.refresh_from_db()
    assert session.temporary_name == ""
    assert session.state == ChatSession.State.PRODUCT_SEARCH
    assert session.active_cart_id is not None
    assert send.call_args[0][2] == SUPPORT_PAYMENT_BACKUP_SALE_MESSAGE


@pytest.mark.django_db
def test_support_details_general_enters_waiting_queue():
    tenant = TenantFactory()
    instance = WhatsappInstanceFactory(tenant=tenant)
    resident = ResidentFactory(tenant=tenant, phone_number="5511999887766")
    session = ChatSessionFactory(
        tenant=tenant,
        phone_number=resident.phone_number,
        state=ChatSession.State.AWAITING_SUPPORT_DETAILS,
        temporary_name=MENU_BILLING,
        is_bot_active=True,
    )

    with (
        mock.patch(
            "apps.sales.services.cart_flow.classify_user_intent",
            return_value="GENERAL",
        ),
        mock.patch("apps.sales.services.cart_flow.send_whatsapp_reply") as send,
        mock.patch(
            "apps.sales.services.cart_flow.handle_complaint",
        ) as complaint,
        mock.patch(
            "apps.sales.services.cart_flow.route_idle_message",
        ) as route_idle,
    ):
        with tenant_scope(tenant.id):
            handled = process_cart_flow(
                tenant.id,
                instance,
                resident.phone_number,
                _event_text("Produto X sem preço na gôndola"),
            )

    assert handled is True
    session.refresh_from_db()
    assert session.state == ChatSession.State.WAITING_FOR_HUMAN
    assert session.is_bot_active is True
    assert session.temporary_name == ""
    assert send.call_args[0][2] == SUPPORT_WAITING_QUEUE_MESSAGE
    assert "digite SAIR" in send.call_args[0][2]
    complaint.assert_not_called()
    route_idle.assert_not_called()


@pytest.mark.django_db
def test_support_details_complaint_queues_for_human():
    tenant = TenantFactory()
    instance = WhatsappInstanceFactory(tenant=tenant)
    resident = ResidentFactory(tenant=tenant, phone_number="5511999887766")
    session = ChatSessionFactory(
        tenant=tenant,
        phone_number=resident.phone_number,
        state=ChatSession.State.AWAITING_SUPPORT_DETAILS,
        temporary_name=MENU_BILLING,
        is_bot_active=True,
    )
    detail = "fui comprar um leite e estava vencido"

    with (
        mock.patch(
            "apps.sales.services.cart_flow.classify_user_intent",
            return_value="COMPLAINT",
        ),
        mock.patch(
            "apps.sales.services.cart_flow.handle_complaint",
            return_value=True,
        ) as complaint,
        mock.patch("apps.sales.services.cart_flow.send_whatsapp_reply") as send,
    ):
        with tenant_scope(tenant.id):
            handled = process_cart_flow(
                tenant.id,
                instance,
                resident.phone_number,
                _event_text(detail),
            )

    assert handled is True
    complaint.assert_called_once()
    assert complaint.call_args.kwargs["message"] == detail
    assert complaint.call_args.kwargs["queue_for_human"] is True
    session.refresh_from_db()
    assert session.state == ChatSession.State.WAITING_FOR_HUMAN
    assert session.is_bot_active is True
    assert send.call_args[0][2] == SUPPORT_WAITING_QUEUE_MESSAGE


@pytest.mark.django_db
def test_support_details_alerta_qualidade_queues_without_pausing():
    tenant = TenantFactory(phone="5511888777666")
    market = MarketFactory(tenant=tenant)
    instance = WhatsappInstanceFactory(tenant=tenant)
    resident = ResidentFactory(
        tenant=tenant,
        market=market,
        phone_number="5511999887766",
        name="Maria Silva",
    )
    session = ChatSessionFactory(
        tenant=tenant,
        phone_number=resident.phone_number,
        state=ChatSession.State.AWAITING_SUPPORT_DETAILS,
        temporary_name="menu:product",
        is_bot_active=True,
    )
    detail = "fui comprar um leite e estava vencido"

    with (
        mock.patch(
            "apps.sales.services.cart_flow.classify_user_intent",
            return_value="COMPLAINT",
        ),
        mock.patch(
            "apps.sales.services.active_bot_router.complete_with_session_history",
            return_value=(
                "[ALERTA_QUALIDADE] Pergunte o valor do estorno, por favor."
            ),
        ),
        mock.patch(
            "apps.chatbot.services.occurrence_dispatch.notify_owner_support_issue",
        ),
        mock.patch(
            "apps.sales.services.active_bot_router.send_whatsapp_reply",
        ) as send_handler,
        mock.patch(
            "apps.sales.services.cart_flow.send_whatsapp_reply",
        ) as send_queue,
    ):
        with tenant_scope(tenant.id):
            handled = process_cart_flow(
                tenant.id,
                instance,
                resident.phone_number,
                _event_text(detail),
            )

    assert handled is True
    session.refresh_from_db()
    assert session.is_bot_active is True
    assert session.state == ChatSession.State.WAITING_FOR_HUMAN
    send_handler.assert_not_called()
    assert send_queue.call_args[0][2] == SUPPORT_WAITING_QUEUE_MESSAGE
    assert "digite SAIR" in send_queue.call_args[0][2]


@pytest.mark.django_db
def test_waiting_for_human_ignores_text_keeps_bot_active():
    tenant = TenantFactory()
    instance = WhatsappInstanceFactory(tenant=tenant)
    resident = ResidentFactory(tenant=tenant, phone_number="5511999887766")
    session = ChatSessionFactory(
        tenant=tenant,
        phone_number=resident.phone_number,
        state=ChatSession.State.WAITING_FOR_HUMAN,
        is_bot_active=True,
    )

    with mock.patch("apps.sales.services.cart_flow.send_whatsapp_reply") as send:
        with tenant_scope(tenant.id):
            handled = process_cart_flow(
                tenant.id,
                instance,
                resident.phone_number,
                _event_text("olá"),
            )

    assert handled is True
    session.refresh_from_db()
    assert session.state == ChatSession.State.WAITING_FOR_HUMAN
    assert session.is_bot_active is True
    send.assert_not_called()


@pytest.mark.django_db
def test_waiting_for_human_sair_shows_main_menu():
    tenant = TenantFactory()
    instance = WhatsappInstanceFactory(tenant=tenant)
    resident = ResidentFactory(tenant=tenant, phone_number="5511999887766", name="Ana")
    session = ChatSessionFactory(
        tenant=tenant,
        phone_number=resident.phone_number,
        state=ChatSession.State.WAITING_FOR_HUMAN,
        is_bot_active=True,
    )

    with mock.patch("apps.sales.services.main_menu.send_whatsapp_reply") as send:
        with tenant_scope(tenant.id):
            handled = process_cart_flow(
                tenant.id,
                instance,
                resident.phone_number,
                _event_text("SAIR"),
            )

    assert handled is True
    session.refresh_from_db()
    assert session.state == ChatSession.State.AWAITING_MAIN_MENU
    assert session.is_bot_active is True
    send.assert_called_once()
    assert "1 —" in send.call_args[0][2]


@pytest.mark.django_db
def test_product_suggestion_notifies_owner_and_panel():
    """Fluxo legado AWAITING_PRODUCT_SUGGESTION (fora do menu) permanece."""
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

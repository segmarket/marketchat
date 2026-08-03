from decimal import Decimal
from unittest import mock

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from apps.demo.services.chat import DEMO_BLOCKING_RESET_MESSAGE, session_id_to_demo_phone
from apps.demo.services.portal import ensure_demo_portal
from apps.integrations.services.webhook_handlers import _handle_message
from apps.integrations.services.webhook_parser import EvolutionWebhookEvent
from apps.residents.models import ChatSession, Resident
from apps.sales.models import Cart
from apps.sales.services.cart_flow import PAYMENT_WAITING_MESSAGE, process_cart_flow
from apps.sales.services.cart_session import unlock_resident_chat_session
from apps.tenants.context import tenant_scope
from tests.factories import (
    ChatSessionFactory,
    ProductFactory,
    ResidentFactory,
    TenantFactory,
    WhatsappInstanceFactory,
)


def _event_text(text: str, phone: str = "5511999887766") -> EvolutionWebhookEvent:
    return EvolutionWebhookEvent(
        event_type="MESSAGE",
        instance_key="test",
        connection_state="",
        remote_jid=f"{phone}@s.whatsapp.net",
        message_id="msg-1",
        from_me=False,
        message_text=text,
        message_kind="text",
    )


@pytest.mark.django_db
def test_awaiting_payment_ok_pago_does_not_search():
    tenant = TenantFactory()
    instance = WhatsappInstanceFactory(tenant=tenant)
    resident = ResidentFactory(tenant=tenant, phone_number="5511999887766")
    product = ProductFactory(tenant=tenant, name="Coca-Cola 2L")
    cart = Cart.objects.create(
        tenant=tenant,
        resident=resident,
        status=Cart.Status.AWAITING_PAYMENT,
        total_value=Decimal("12.50"),
    )
    session = ChatSessionFactory(
        tenant=tenant,
        phone_number=resident.phone_number,
        state=ChatSession.State.IDLE,
        active_cart=cart,
        last_discussed_product=product,
        temporary_name=product.sku,
        pending_intent="compra",
    )

    with (
        mock.patch("apps.sales.services.cart_flow.send_whatsapp_reply") as send,
        mock.patch("apps.sales.services.cart_flow.route_idle_message") as route_idle,
        mock.patch(
            "apps.sales.services.cart_flow.classify_user_intent",
        ) as classify,
    ):
        with tenant_scope(tenant.id):
            handled = process_cart_flow(
                tenant.id,
                instance,
                resident.phone_number,
                _event_text("Ok, pago"),
            )

    assert handled is True
    send.assert_called_once()
    assert send.call_args[0][2] == PAYMENT_WAITING_MESSAGE
    route_idle.assert_not_called()
    classify.assert_not_called()
    session.refresh_from_db()
    assert session.state == ChatSession.State.IDLE
    assert session.active_cart_id == cart.id


@pytest.mark.django_db
def test_unlock_clears_pending_intent():
    tenant = TenantFactory()
    resident = ResidentFactory(tenant=tenant, phone_number="5511999887766")
    ChatSessionFactory(
        tenant=tenant,
        phone_number=resident.phone_number,
        state=ChatSession.State.IDLE,
        pending_intent="reclamacao",
        temporary_name="SKU1",
    )
    unlock_resident_chat_session(resident=resident, clear_cart_link=True)
    session = ChatSession.objects.get(tenant=tenant, phone_number=resident.phone_number)
    assert session.pending_intent == ""
    assert session.temporary_name == ""
    assert session.last_discussed_product_id is None


@pytest.mark.django_db
def test_demo_waiting_for_human_auto_resets_with_simulation_message():
    client = APIClient()
    session_id = "55555555-5555-4555-8555-555555555555"
    phone = session_id_to_demo_phone(session_id)
    bundle = ensure_demo_portal()

    with tenant_scope(bundle.tenant.id):
        Resident.objects.create(
            tenant=bundle.tenant,
            market=bundle.market,
            phone_number=phone,
            name="Muted Demo",
        )
        ChatSession.objects.create(
            tenant=bundle.tenant,
            phone_number=phone,
            state=ChatSession.State.WAITING_FOR_HUMAN,
            is_bot_active=True,
            pending_intent="reclamacao",
        )

    with mock.patch(
        "apps.integrations.services.evolution_client.EvolutionClient.send_text"
    ):
        response = client.post(
            reverse("demo-chat"),
            {"message": "R$ 12,90", "session_id": session_id},
            format="json",
        )

    assert response.status_code == 200
    assert DEMO_BLOCKING_RESET_MESSAGE in response.json()["reply"]
    with tenant_scope(bundle.tenant.id):
        session = ChatSession.objects.get(tenant=bundle.tenant, phone_number=phone)
        assert session.state == ChatSession.State.IDLE
        assert session.pending_intent == ""
        assert session.is_bot_active is True


@pytest.mark.django_db
def test_demo_heals_paused_bot_in_product_search():
    """Sessão demo com is_bot_active=False + PRODUCT_SEARCH não deve engolir a mensagem."""
    client = APIClient()
    session_id = "66666666-6666-4666-8666-666666666666"
    phone = session_id_to_demo_phone(session_id)
    bundle = ensure_demo_portal()

    with tenant_scope(bundle.tenant.id):
        Resident.objects.create(
            tenant=bundle.tenant,
            market=bundle.market,
            phone_number=phone,
            name="Stuck Demo",
        )
        session = ChatSession.objects.create(
            tenant=bundle.tenant,
            phone_number=phone,
            state=ChatSession.State.PRODUCT_SEARCH,
            is_bot_active=False,
        )

    with mock.patch(
        "apps.integrations.services.evolution_client.EvolutionClient.send_text"
    ):
        with mock.patch(
            "apps.demo.services.chat.process_cart_flow",
            return_value=True,
        ) as cart:
            response = client.post(
                reverse("demo-chat"),
                {"message": "Oi", "session_id": session_id},
                format="json",
            )

    assert response.status_code == 200
    cart.assert_called_once()
    session.refresh_from_db()
    assert session.is_bot_active is True


@pytest.mark.django_db
def test_webhook_waiting_for_human_logs_and_skips_cart():
    tenant = TenantFactory()
    instance = WhatsappInstanceFactory(tenant=tenant, instance_name="mc-mute-test")
    resident = ResidentFactory(tenant=tenant, phone_number="5511999887766")
    ChatSessionFactory(
        tenant=tenant,
        phone_number=resident.phone_number,
        state=ChatSession.State.WAITING_FOR_HUMAN,
        is_bot_active=True,
    )
    event = EvolutionWebhookEvent(
        event_type="MESSAGE",
        instance_key=instance.instance_name,
        connection_state="",
        remote_jid=f"{resident.phone_number}@s.whatsapp.net",
        message_id="mute-1",
        from_me=False,
        message_text="R$ 12,90",
        message_kind="text",
    )

    with (
        mock.patch(
            "apps.integrations.services.webhook_handlers.process_cart_flow",
        ) as cart,
        mock.patch(
            "apps.integrations.services.webhook_handlers.send_whatsapp_reply",
        ) as send,
        mock.patch(
            "apps.integrations.services.webhook_handlers.run_chatbot_flow",
        ) as bot,
    ):
        with tenant_scope(tenant.id):
            _handle_message(event, instance)

    cart.assert_not_called()
    bot.assert_not_called()
    send.assert_not_called()

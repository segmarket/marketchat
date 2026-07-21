from datetime import timedelta
from unittest.mock import patch

import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework_simplejwt.tokens import RefreshToken

from apps.chatbot.models import ChatMessageLog
from apps.chatbot.services.human_handover import (
    HUMAN_HANDOVER_TIMEOUT,
    ensure_bot_active_or_timeout,
    pause_bot,
    resume_bot,
    toggle_bot,
)
from apps.integrations.services.webhook_handlers import _handle_message
from apps.integrations.services.webhook_parser import EvolutionWebhookEvent
from apps.residents.models import ChatSession
from tests.factories import (
    ChatSessionFactory,
    MarketFactory,
    ResidentFactory,
    TenantFactory,
    UserFactory,
    WhatsappInstanceFactory,
)


def _auth(client, user):
    client.credentials(
        HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(user).access_token}",
    )


@pytest.mark.django_db
def test_pause_and_resume_bot():
    session = ChatSessionFactory(state=ChatSession.State.IDLE)
    assert session.is_bot_active is True

    pause_bot(session)
    session.refresh_from_db()
    assert session.is_bot_active is False
    assert session.last_human_interaction_at is not None

    resume_bot(session)
    session.refresh_from_db()
    assert session.is_bot_active is True


@pytest.mark.django_db
def test_ensure_bot_active_or_timeout_reactivates_after_2h():
    session = ChatSessionFactory(state=ChatSession.State.IDLE)
    pause_bot(session)
    ChatSession.objects.filter(pk=session.pk).update(
        last_human_interaction_at=timezone.now() - HUMAN_HANDOVER_TIMEOUT - timedelta(minutes=1),
    )
    session.refresh_from_db()

    assert ensure_bot_active_or_timeout(session) is True
    session.refresh_from_db()
    assert session.is_bot_active is True


@pytest.mark.django_db
def test_ensure_bot_active_or_timeout_keeps_paused_within_window():
    session = ChatSessionFactory(state=ChatSession.State.IDLE)
    pause_bot(session)
    session.refresh_from_db()

    assert ensure_bot_active_or_timeout(session) is False
    session.refresh_from_db()
    assert session.is_bot_active is False


@pytest.mark.django_db
def test_toggle_bot_endpoint(api_client):
    tenant = TenantFactory()
    user = UserFactory(tenant=tenant, email="handover-toggle@example.com")
    session = ChatSessionFactory(tenant=tenant, state=ChatSession.State.IDLE)
    _auth(api_client, user)

    url = reverse("chatbot-session-toggle-bot", kwargs={"pk": session.pk})
    resp = api_client.patch(url, {"is_bot_active": False}, format="json")
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_bot_active"] is False
    assert data["last_human_interaction_at"] is not None

    session.refresh_from_db()
    assert session.is_bot_active is False

    resp = api_client.patch(url, {"is_bot_active": True}, format="json")
    assert resp.status_code == 200
    assert resp.json()["is_bot_active"] is True


@pytest.mark.django_db
@patch("apps.chatbot.views_handover.send_whatsapp_reply")
def test_agent_message_pauses_bot(mock_send, api_client):
    tenant = TenantFactory()
    user = UserFactory(tenant=tenant, email="handover-msg@example.com")
    WhatsappInstanceFactory(tenant=tenant, is_active=True)
    session = ChatSessionFactory(
        tenant=tenant,
        phone_number="5511999990001",
        state=ChatSession.State.IDLE,
    )
    _auth(api_client, user)

    url = reverse("chatbot-session-agent-message", kwargs={"pk": session.pk})
    resp = api_client.post(url, {"text": "Olá, sou o atendente"}, format="json")
    assert resp.status_code == 201
    data = resp.json()
    assert data["is_bot_active"] is False
    assert data["message"]["direction"] == ChatMessageLog.Direction.AGENT
    assert data["message"]["message_text"] == "Olá, sou o atendente"
    mock_send.assert_called_once()

    session.refresh_from_db()
    assert session.is_bot_active is False
    assert ChatMessageLog.all_objects.filter(
        session=session,
        direction=ChatMessageLog.Direction.AGENT,
    ).exists()


@pytest.mark.django_db
@patch("apps.integrations.services.webhook_handlers.run_chatbot_flow")
@patch("apps.integrations.services.webhook_handlers.process_cart_flow", return_value=False)
@patch("apps.integrations.services.webhook_handlers.classify_user_intent", return_value="GENERAL")
@patch(
    "apps.integrations.services.webhook_handlers.resident_has_completed_onboarding",
    return_value=True,
)
def test_webhook_skips_bot_when_paused(
    _mock_onboarded,
    _mock_intent,
    _mock_cart,
    mock_flow,
):
    tenant = TenantFactory()
    market = MarketFactory(tenant=tenant)
    resident = ResidentFactory(tenant=tenant, market=market, phone_number="5511888777666")
    instance = WhatsappInstanceFactory(tenant=tenant, is_active=True)
    session = ChatSessionFactory(
        tenant=tenant,
        phone_number=resident.phone_number,
        state=ChatSession.State.IDLE,
    )
    pause_bot(session)

    event = EvolutionWebhookEvent(
        event_type="MESSAGES.UPSERT",
        instance_key=instance.instance_name,
        connection_state="",
        remote_jid=f"{resident.phone_number}@s.whatsapp.net",
        message_id="msg-handover-1",
        from_me=False,
        message_text="Preciso de ajuda",
        message_kind="text",
        raw_message={},
    )
    _handle_message(event, instance)

    mock_flow.assert_not_called()
    assert ChatMessageLog.all_objects.filter(
        session=session,
        direction=ChatMessageLog.Direction.INBOUND,
        message_text="Preciso de ajuda",
    ).exists()


@pytest.mark.django_db
@patch("apps.integrations.services.webhook_handlers.run_chatbot_flow", return_value=True)
@patch("apps.integrations.services.webhook_handlers.process_cart_flow", return_value=False)
@patch("apps.integrations.services.webhook_handlers.classify_user_intent", return_value="GENERAL")
@patch(
    "apps.integrations.services.webhook_handlers.resident_has_completed_onboarding",
    return_value=True,
)
def test_webhook_reactivates_bot_after_timeout(
    _mock_onboarded,
    _mock_intent,
    _mock_cart,
    mock_flow,
):
    tenant = TenantFactory()
    market = MarketFactory(tenant=tenant)
    resident = ResidentFactory(tenant=tenant, market=market, phone_number="5511777666555")
    instance = WhatsappInstanceFactory(tenant=tenant, is_active=True)
    session = ChatSessionFactory(
        tenant=tenant,
        phone_number=resident.phone_number,
        state=ChatSession.State.IDLE,
    )
    pause_bot(session)
    ChatSession.objects.filter(pk=session.pk).update(
        last_human_interaction_at=timezone.now() - HUMAN_HANDOVER_TIMEOUT - timedelta(minutes=5),
    )

    event = EvolutionWebhookEvent(
        event_type="MESSAGES.UPSERT",
        instance_key=instance.instance_name,
        connection_state="",
        remote_jid=f"{resident.phone_number}@s.whatsapp.net",
        message_id="msg-handover-2",
        from_me=False,
        message_text="Oi de novo",
        message_kind="text",
        raw_message={},
    )
    _handle_message(event, instance)

    mock_flow.assert_called_once()
    session.refresh_from_db()
    assert session.is_bot_active is True


@pytest.mark.django_db
def test_conversation_includes_bot_status(api_client):
    tenant = TenantFactory()
    user = UserFactory(tenant=tenant, email="handover-conv@example.com")
    market = MarketFactory(tenant=tenant)
    resident = ResidentFactory(tenant=tenant, market=market)
    session = ChatSessionFactory(
        tenant=tenant,
        phone_number=resident.phone_number,
        state=ChatSession.State.IDLE,
    )
    toggle_bot(session, is_bot_active=False)
    ChatMessageLog.all_objects.create(
        tenant=tenant,
        session=session,
        resident=resident,
        market=market,
        message_text="Oi",
        direction=ChatMessageLog.Direction.INBOUND,
    )
    _auth(api_client, user)

    resp = api_client.get(
        reverse("chatbot-logs-conversation"),
        {"session_id": session.pk},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_bot_active"] is False
    assert data["last_human_interaction_at"] is not None

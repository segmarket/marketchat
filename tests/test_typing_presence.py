import pytest
from django.core.cache import cache
from django.urls import reverse
from rest_framework_simplejwt.tokens import RefreshToken

from apps.chatbot.models import ChatMessageLog
from apps.chatbot.services.typing_presence import (
    clear_typing,
    is_client_typing,
    mark_typing,
)
from apps.integrations.services.webhook_handlers import handle_evolution_webhook
from apps.integrations.services.webhook_parser import parse_evolution_payload
from apps.residents.models import ChatSession
from tests.factories import (
    ChatSessionFactory,
    TenantFactory,
    UserFactory,
    WhatsappInstanceFactory,
)


@pytest.fixture(autouse=True)
def _clear_cache():
    cache.clear()
    yield
    cache.clear()


@pytest.mark.django_db
def test_mark_clear_is_client_typing():
    assert is_client_typing(1, 99) is False
    mark_typing(1, 99)
    assert is_client_typing(1, 99) is True
    clear_typing(1, 99)
    assert is_client_typing(1, 99) is False


@pytest.mark.django_db
def test_presence_composing_marks_typing_cache():
    tenant = TenantFactory()
    instance = WhatsappInstanceFactory(tenant=tenant)
    phone = "5511999887766"
    ChatSessionFactory(tenant=tenant, phone_number=phone)

    event = parse_evolution_payload(
        {
            "event": "PRESENCE",
            "instance": instance.instance_name,
            "data": {
                "remoteJid": f"{phone}@s.whatsapp.net",
                "presence": "composing",
            },
        },
    )
    assert event is not None
    assert event.presence == "composing"
    handle_evolution_webhook(event, instance)

    session = ChatSession.objects.get(tenant_id=tenant.id, phone_number=phone)
    assert is_client_typing(tenant.id, session.id) is True


@pytest.mark.django_db
def test_presence_paused_clears_typing_cache():
    tenant = TenantFactory()
    instance = WhatsappInstanceFactory(tenant=tenant)
    phone = "5511888776655"
    session = ChatSessionFactory(tenant=tenant, phone_number=phone)
    mark_typing(tenant.id, session.id)

    event = parse_evolution_payload(
        {
            "event": "PRESENCE_UPDATE",
            "instance": instance.instance_name,
            "data": {
                "Chat": f"{phone}@s.whatsapp.net",
                "presence": "paused",
            },
        },
    )
    assert event is not None
    handle_evolution_webhook(event, instance)
    assert is_client_typing(tenant.id, session.id) is False


@pytest.mark.django_db
def test_conversation_returns_client_is_typing(api_client):
    tenant = TenantFactory()
    user = UserFactory(tenant=tenant, email="typing-api@example.com")
    session = ChatSessionFactory(tenant=tenant, phone_number="5511777665544")
    ChatMessageLog.all_objects.create(
        tenant=tenant,
        session=session,
        message_text="Oi",
        direction=ChatMessageLog.Direction.INBOUND,
        message_kind=ChatMessageLog.MessageKind.TEXT,
    )
    mark_typing(tenant.id, session.id)

    api_client.credentials(
        HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(user).access_token}",
    )
    url = reverse("chatbot-logs-conversation")
    resp = api_client.get(url, {"session_id": session.id})
    assert resp.status_code == 200
    data = resp.json()
    assert data["client_is_typing"] is True

    clear_typing(tenant.id, session.id)
    resp = api_client.get(url, {"session_id": session.id})
    assert resp.status_code == 200
    assert resp.json()["client_is_typing"] is False

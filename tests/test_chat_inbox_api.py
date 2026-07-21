from datetime import timedelta

import pytest
from django.test.utils import CaptureQueriesContext
from django.db import connection
from django.urls import reverse
from django.utils import timezone
from rest_framework_simplejwt.tokens import RefreshToken

from apps.chatbot.models import ChatMessageLog
from apps.chatbot.services.human_handover import pause_bot
from tests.factories import (
    ChatSessionFactory,
    MarketFactory,
    ResidentFactory,
    TenantFactory,
    UserFactory,
)


def _auth(client, user):
    client.credentials(
        HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(user).access_token}",
    )


def _log(*, tenant, session, resident=None, market=None, direction="INBOUND", text="Oi", created_at=None):
    log = ChatMessageLog.all_objects.create(
        tenant=tenant,
        session=session,
        resident=resident,
        market=market or (resident.market if resident else None),
        message_text=text,
        direction=direction,
        message_kind=ChatMessageLog.MessageKind.TEXT,
    )
    if created_at:
        ChatMessageLog.all_objects.filter(pk=log.pk).update(created_at=created_at)
        log.refresh_from_db()
    return log


@pytest.mark.django_db
def test_inbox_sessions_filter_bot_active(api_client):
    tenant = TenantFactory()
    user = UserFactory(tenant=tenant, email="inbox-filter@example.com")
    market = MarketFactory(tenant=tenant)
    r1 = ResidentFactory(tenant=tenant, market=market, name="Ana")
    r2 = ResidentFactory(tenant=tenant, market=market, name="Bruno")
    s_waiting = ChatSessionFactory(
        tenant=tenant,
        phone_number=r1.phone_number,
        is_bot_active=False,
    )
    s_bot = ChatSessionFactory(
        tenant=tenant,
        phone_number=r2.phone_number,
        is_bot_active=True,
    )
    now = timezone.now()
    _log(tenant=tenant, session=s_waiting, resident=r1, text="Preciso de ajuda", created_at=now)
    _log(tenant=tenant, session=s_bot, resident=r2, text="Quero comprar", created_at=now - timedelta(minutes=1))
    pause_bot(s_waiting)

    _auth(api_client, user)
    url = reverse("chatbot-sessions-inbox")

    resp = api_client.get(url, {"bot_active": "false"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["count"] == 1
    assert data["results"][0]["session_id"] == s_waiting.id
    assert data["results"][0]["is_bot_active"] is False
    assert data["results"][0]["last_inbound_id"] is not None

    resp = api_client.get(url, {"bot_active": "true"})
    assert resp.status_code == 200
    assert resp.json()["count"] == 1
    assert resp.json()["results"][0]["session_id"] == s_bot.id

    resp = api_client.get(url)
    assert resp.status_code == 200
    assert resp.json()["count"] == 2


@pytest.mark.django_db
def test_conversation_after_id_incremental(api_client):
    tenant = TenantFactory()
    user = UserFactory(tenant=tenant, email="inbox-after@example.com")
    market = MarketFactory(tenant=tenant)
    resident = ResidentFactory(tenant=tenant, market=market)
    session = ChatSessionFactory(tenant=tenant, phone_number=resident.phone_number)
    m1 = _log(tenant=tenant, session=session, resident=resident, text="1")
    m2 = _log(tenant=tenant, session=session, resident=resident, text="2")
    m3 = _log(tenant=tenant, session=session, resident=resident, text="3")

    _auth(api_client, user)
    url = reverse("chatbot-logs-conversation")
    resp = api_client.get(url, {"session_id": session.id, "after_id": m1.id})
    assert resp.status_code == 200
    data = resp.json()
    ids = [m["id"] for m in data["messages"]]
    assert ids == [m2.id, m3.id]
    assert data["is_bot_active"] is True


@pytest.mark.django_db
def test_inbox_sessions_query_budget(api_client):
    tenant = TenantFactory()
    user = UserFactory(tenant=tenant, email="inbox-queries@example.com")
    market = MarketFactory(tenant=tenant)
    now = timezone.now()
    for i in range(8):
        resident = ResidentFactory(tenant=tenant, market=market, name=f"Morador {i}")
        session = ChatSessionFactory(tenant=tenant, phone_number=resident.phone_number)
        _log(
            tenant=tenant,
            session=session,
            resident=resident,
            text=f"msg {i}",
            created_at=now - timedelta(minutes=i),
        )

    _auth(api_client, user)
    url = reverse("chatbot-sessions-inbox")
    with CaptureQueriesContext(connection) as ctx:
        resp = api_client.get(url)
    assert resp.status_code == 200
    assert resp.json()["count"] == 8
    # Auth + listagem anotada + latest logs + inbound ids + residents (sem N+1 por sessão).
    assert len(ctx.captured_queries) < 25

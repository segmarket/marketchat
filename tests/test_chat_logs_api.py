from datetime import timedelta
from io import BytesIO

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from django.utils import timezone
from rest_framework_simplejwt.tokens import RefreshToken

from apps.chatbot.models import ChatMessageLog
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


def _create_log(
    *,
    tenant,
    session,
    resident=None,
    market=None,
    direction=ChatMessageLog.Direction.INBOUND,
    intent_type="",
    message_text="Olá",
    created_at=None,
    message_kind=ChatMessageLog.MessageKind.TEXT,
    attachment=None,
):
    log = ChatMessageLog.all_objects.create(
        tenant=tenant,
        session=session,
        resident=resident,
        market=market or (resident.market if resident else None),
        message_text=message_text,
        direction=direction,
        intent_type=intent_type,
        message_kind=message_kind,
    )
    if created_at:
        ChatMessageLog.all_objects.filter(pk=log.pk).update(created_at=created_at)
        log.refresh_from_db()
    if attachment:
        log.attachment.save(attachment.name, attachment, save=True)
    return log


@pytest.mark.django_db
def test_chat_logs_grouping_same_session_same_day(api_client):
    tenant = TenantFactory()
    user = UserFactory(tenant=tenant, email="logs-group@example.com")
    market = MarketFactory(tenant=tenant, name="Condomínio Alpha")
    resident = ResidentFactory(tenant=tenant, market=market, name="Ana Silva")
    session = ChatSessionFactory(tenant=tenant, phone_number=resident.phone_number)
    now = timezone.now()

    _create_log(
        tenant=tenant,
        session=session,
        resident=resident,
        message_text="Quero comprar",
        intent_type=ChatMessageLog.IntentType.PURCHASE,
        created_at=now,
    )
    _create_log(
        tenant=tenant,
        session=session,
        resident=resident,
        direction=ChatMessageLog.Direction.OUTBOUND,
        message_text="Ok, envie a foto",
        created_at=now + timedelta(minutes=1),
    )

    _auth(api_client, user)
    resp = api_client.get(reverse("chatbot-logs-list"))
    assert resp.status_code == 200
    data = resp.json()
    assert data["count"] == 1
    row = data["results"][0]
    assert row["session_id"] == session.id
    assert row["message_count"] == 2
    assert row["resident_name"] == "Ana Silva"
    assert row["market_name"] == "Condomínio Alpha"


@pytest.mark.django_db
def test_chat_logs_filter_intent_and_market(api_client):
    tenant = TenantFactory()
    user = UserFactory(tenant=tenant, email="logs-filter@example.com")
    market_a = MarketFactory(tenant=tenant, name="Mercado A")
    market_b = MarketFactory(tenant=tenant, name="Mercado B")
    resident_a = ResidentFactory(tenant=tenant, market=market_a, name="Carlos")
    resident_b = ResidentFactory(tenant=tenant, market=market_b, name="Bruno")
    session_a = ChatSessionFactory(tenant=tenant, phone_number=resident_a.phone_number)
    session_b = ChatSessionFactory(tenant=tenant, phone_number=resident_b.phone_number)
    now = timezone.now()

    _create_log(
        tenant=tenant,
        session=session_a,
        resident=resident_a,
        intent_type=ChatMessageLog.IntentType.MAINTENANCE_ISSUE,
        message_text="Porta quebrada",
        created_at=now,
    )
    _create_log(
        tenant=tenant,
        session=session_b,
        resident=resident_b,
        intent_type=ChatMessageLog.IntentType.PURCHASE,
        message_text="Quero água",
        created_at=now,
    )

    _auth(api_client, user)
    resp = api_client.get(
        reverse("chatbot-logs-list"),
        {"intent_type": "MAINTENANCE_ISSUE", "market_id": market_a.id},
    )
    assert resp.status_code == 200
    results = resp.json()["results"]
    assert len(results) == 1
    assert results[0]["resident_name"] == "Carlos"
    assert results[0]["intent_type"] == ChatMessageLog.IntentType.MAINTENANCE_ISSUE


@pytest.mark.django_db
def test_chat_logs_tenant_isolation(api_client):
    tenant_a = TenantFactory()
    tenant_b = TenantFactory()
    user_a = UserFactory(tenant=tenant_a, email="logs-tenant-a@example.com")
    user_b = UserFactory(tenant=tenant_b, email="logs-tenant-b@example.com")

    session_a = ChatSessionFactory(tenant=tenant_a)
    session_b = ChatSessionFactory(tenant=tenant_b)
    _create_log(
        tenant=tenant_a,
        session=session_a,
        message_text="msg A",
        created_at=timezone.now(),
    )
    _create_log(
        tenant=tenant_b,
        session=session_b,
        message_text="msg B",
        created_at=timezone.now(),
    )

    _auth(api_client, user_a)
    resp_a = api_client.get(reverse("chatbot-logs-list"))
    assert resp_a.status_code == 200
    assert resp_a.json()["count"] == 1

    _auth(api_client, user_b)
    resp_b = api_client.get(reverse("chatbot-logs-list"))
    assert resp_b.json()["count"] == 1


@pytest.mark.django_db
def test_chat_logs_pagination(api_client):
    tenant = TenantFactory()
    user = UserFactory(tenant=tenant, email="logs-page@example.com")
    now = timezone.now()

    for i in range(25):
        session = ChatSessionFactory(tenant=tenant, phone_number=f"551199900{i:04d}")
        _create_log(
            tenant=tenant,
            session=session,
            message_text=f"msg {i}",
            created_at=now - timedelta(days=i),
        )

    _auth(api_client, user)
    page1 = api_client.get(reverse("chatbot-logs-list"), {"page": 1})
    assert page1.status_code == 200
    body1 = page1.json()
    assert body1["count"] == 25
    assert len(body1["results"]) == 20
    assert body1["next"] == 2

    page2 = api_client.get(reverse("chatbot-logs-list"), {"page": 2})
    assert len(page2.json()["results"]) == 5


@pytest.mark.django_db
def test_chat_logs_conversation_with_image(api_client):
    tenant = TenantFactory()
    user = UserFactory(tenant=tenant, email="logs-conv@example.com")
    market = MarketFactory(tenant=tenant)
    resident = ResidentFactory(tenant=tenant, market=market)
    session = ChatSessionFactory(tenant=tenant, phone_number=resident.phone_number)
    now = timezone.now()
    day = timezone.localdate(now)

    _create_log(
        tenant=tenant,
        session=session,
        resident=resident,
        message_text="[Foto dos produtos]",
        intent_type=ChatMessageLog.IntentType.PURCHASE,
        message_kind=ChatMessageLog.MessageKind.IMAGE,
        created_at=now,
        attachment=SimpleUploadedFile(
            "foto.jpg",
            BytesIO(b"fake-image-bytes").getvalue(),
            content_type="image/jpeg",
        ),
    )

    _auth(api_client, user)
    resp = api_client.get(
        reverse("chatbot-logs-conversation"),
        {"session_id": session.id, "date": day.isoformat()},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["messages"]) == 1
    msg = body["messages"][0]
    assert msg["direction"] == ChatMessageLog.Direction.INBOUND
    assert msg["message_kind"] == ChatMessageLog.MessageKind.IMAGE
    assert msg["attachment_url"]
    assert "/media/" in msg["attachment_url"]
    assert msg["attachment_url"].startswith("http")

    media_path = msg["attachment_url"].split("/media/", 1)[1]
    media_resp = api_client.get(f"/media/{media_path}")
    assert media_resp.status_code == 200
    body_bytes = b"".join(media_resp.streaming_content)
    assert body_bytes == b"fake-image-bytes"
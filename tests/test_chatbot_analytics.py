from datetime import datetime, timedelta

import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework_simplejwt.tokens import RefreshToken

from apps.chatbot.models import ChatMessageLog
from apps.chatbot.services.chatbot_analytics import (
    AnalyticsFilters,
    compute_chatbot_analytics,
)
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
):
    log = ChatMessageLog.all_objects.create(
        tenant=tenant,
        session=session,
        resident=resident,
        market=market or (resident.market if resident else None),
        message_text=message_text,
        direction=direction,
        intent_type=intent_type,
    )
    if created_at:
        ChatMessageLog.all_objects.filter(pk=log.pk).update(created_at=created_at)
    return log


@pytest.mark.django_db
def test_retention_rate_and_counts():
    tenant = TenantFactory()
    market = MarketFactory(tenant=tenant)
    resident = ResidentFactory(tenant=tenant, market=market)
    now = timezone.now()

    intents = [
        ChatMessageLog.IntentType.PURCHASE,
        ChatMessageLog.IntentType.GENERAL,
        ChatMessageLog.IntentType.STOCK_ISSUE,
        ChatMessageLog.IntentType.PAYMENT_ERROR,
    ]

    for idx, intent in enumerate(intents):
        session = ChatSessionFactory(
            tenant=tenant,
            phone_number=f"551199900{idx:04d}",
        )
        _create_log(
            tenant=tenant,
            session=session,
            resident=resident,
            market=market,
            intent_type=intent,
            created_at=now - timedelta(hours=idx),
        )

    payload = compute_chatbot_analytics(AnalyticsFilters(tenant_id=tenant.id))

    assert payload.retention.automated_sessions_count == 3
    assert payload.retention.support_tickets_count == 1
    assert payload.retention.retention_rate == 75.0
    assert payload.cards.total_interactions == 4
    assert payload.cards.critical_incidents == 1


@pytest.mark.django_db
def test_hourly_distribution_buckets():
    tenant = TenantFactory()
    market = MarketFactory(tenant=tenant)
    resident = ResidentFactory(tenant=tenant, market=market)
    tz = timezone.get_current_timezone()
    today = timezone.localdate()

    hours_and_labels = [
        (2, "00h-06h"),
        (8, "06h-12h"),
        (14, "12h-18h"),
        (20, "18h-00h"),
    ]

    for idx, (hour, _) in enumerate(hours_and_labels):
        session = ChatSessionFactory(
            tenant=tenant,
            phone_number=f"551188800{idx:04d}",
        )
        created_at = timezone.make_aware(
            datetime(today.year, today.month, today.day, hour, 30),
            tz,
        )
        _create_log(
            tenant=tenant,
            session=session,
            resident=resident,
            market=market,
            intent_type=ChatMessageLog.IntentType.GENERAL,
            created_at=created_at,
        )

    payload = compute_chatbot_analytics(AnalyticsFilters(tenant_id=tenant.id))
    by_label = {b.label: b.count for b in payload.hourly_distribution}

    assert by_label["00h-06h"] == 1
    assert by_label["06h-12h"] == 1
    assert by_label["12h-18h"] == 1
    assert by_label["18h-00h"] == 1


@pytest.mark.django_db
def test_tenant_isolation():
    tenant_a = TenantFactory()
    tenant_b = TenantFactory()
    market_a = MarketFactory(tenant=tenant_a)
    resident_a = ResidentFactory(tenant=tenant_a, market=market_a)
    session_a = ChatSessionFactory(tenant=tenant_a)
    _create_log(
        tenant=tenant_a,
        session=session_a,
        resident=resident_a,
        market=market_a,
        intent_type=ChatMessageLog.IntentType.PURCHASE,
    )

    payload_b = compute_chatbot_analytics(AnalyticsFilters(tenant_id=tenant_b.id))
    assert payload_b.cards.total_interactions == 0
    assert payload_b.retention.retention_rate == 0.0


@pytest.mark.django_db
def test_analytics_api_authenticated(api_client):
    tenant = TenantFactory()
    user = UserFactory(tenant=tenant)
    market = MarketFactory(tenant=tenant)
    resident = ResidentFactory(tenant=tenant, market=market)
    session = ChatSessionFactory(tenant=tenant, phone_number=resident.phone_number)
    _create_log(
        tenant=tenant,
        session=session,
        resident=resident,
        market=market,
        intent_type=ChatMessageLog.IntentType.GENERAL,
    )

    _auth(api_client, user)
    resp = api_client.get(reverse("chatbot-analytics"))
    assert resp.status_code == 200
    data = resp.json()
    assert "cards" in data
    assert "retention" in data
    assert "hourly_distribution" in data
    assert len(data["hourly_distribution"]) == 4
    assert len(data["stability_series"]) == 30
    assert data["cards"]["total_interactions"] == 1


@pytest.mark.django_db
def test_analytics_api_without_tenant_returns_400(api_client):
    user = UserFactory(tenant=None)
    _auth(api_client, user)
    resp = api_client.get(reverse("chatbot-analytics"))
    assert resp.status_code == 400


@pytest.mark.django_db
def test_analytics_api_market_filter(api_client):
    tenant = TenantFactory()
    user = UserFactory(tenant=tenant)
    market_a = MarketFactory(tenant=tenant, name="A")
    market_b = MarketFactory(tenant=tenant, name="B")
    resident_a = ResidentFactory(tenant=tenant, market=market_a)
    resident_b = ResidentFactory(tenant=tenant, market=market_b)
    session_a = ChatSessionFactory(tenant=tenant, phone_number=resident_a.phone_number)
    session_b = ChatSessionFactory(tenant=tenant, phone_number=resident_b.phone_number)

    _create_log(
        tenant=tenant,
        session=session_a,
        resident=resident_a,
        market=market_a,
        intent_type=ChatMessageLog.IntentType.GENERAL,
    )
    _create_log(
        tenant=tenant,
        session=session_b,
        resident=resident_b,
        market=market_b,
        intent_type=ChatMessageLog.IntentType.GENERAL,
    )

    _auth(api_client, user)
    resp = api_client.get(
        reverse("chatbot-analytics"),
        {"market_id": market_a.id},
    )
    assert resp.status_code == 200
    assert resp.json()["cards"]["total_interactions"] == 1

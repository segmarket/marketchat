from datetime import datetime, time
from unittest import mock
from zoneinfo import ZoneInfo

import pytest
from django.urls import reverse
from rest_framework_simplejwt.tokens import RefreshToken

from apps.chatbot.models import BotSchedule
from apps.chatbot.services.bot_schedule import should_bot_auto_reply
from apps.integrations.services.webhook_handlers import handle_evolution_webhook
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

SP = ZoneInfo("America/Sao_Paulo")


def _auth(client, user):
    client.credentials(
        HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(user).access_token}",
    )


def _aware(year, month, day, hour, minute=0):
    return datetime(year, month, day, hour, minute, tzinfo=SP)


@pytest.mark.django_db
def test_should_bot_auto_reply_no_rows_always_true():
    tenant = TenantFactory()
    assert should_bot_auto_reply(tenant.id, now=_aware(2026, 7, 20, 3, 0)) is True


@pytest.mark.django_db
def test_should_bot_auto_reply_inactive_day_bot_active_24h():
    tenant = TenantFactory()
    # Monday 2026-07-20 — folga: bot responde o dia todo
    BotSchedule.objects.create(
        tenant=tenant,
        day_of_week=0,
        is_active=False,
        start_time=time(9, 0),
        end_time=time(18, 0),
    )
    assert should_bot_auto_reply(tenant.id, now=_aware(2026, 7, 20, 12, 0)) is True


@pytest.mark.django_db
def test_should_bot_auto_reply_business_hours_mute_bot():
    tenant = TenantFactory()
    BotSchedule.objects.create(
        tenant=tenant,
        day_of_week=0,
        is_active=True,
        start_time=time(9, 0),
        end_time=time(18, 0),
    )
    # Dentro do expediente → bot pausado
    assert should_bot_auto_reply(tenant.id, now=_aware(2026, 7, 20, 9, 0)) is False
    assert should_bot_auto_reply(tenant.id, now=_aware(2026, 7, 20, 12, 0)) is False
    assert should_bot_auto_reply(tenant.id, now=_aware(2026, 7, 20, 18, 0)) is False
    # Fora do expediente → bot assume
    assert should_bot_auto_reply(tenant.id, now=_aware(2026, 7, 20, 8, 59)) is True
    assert should_bot_auto_reply(tenant.id, now=_aware(2026, 7, 20, 18, 1)) is True


@pytest.mark.django_db
def test_bot_schedule_api_get_defaults_and_put(api_client):
    tenant = TenantFactory()
    user = UserFactory(tenant=tenant, email="schedule@example.com")
    _auth(api_client, user)

    url = reverse("settings-bot-schedule")
    get_resp = api_client.get(url)
    assert get_resp.status_code == 200
    body = get_resp.json()
    assert len(body["days"]) == 7
    assert body["is_bot_active_global"] is True
    assert BotSchedule.objects.filter(tenant=tenant).count() == 0

    days = []
    for i in range(7):
        days.append(
            {
                "day_of_week": i,
                "is_active": i < 5,
                "start_time": "08:00:00",
                "end_time": "17:00:00",
            },
        )
    put_resp = api_client.put(url, {"days": days}, format="json")
    assert put_resp.status_code == 200
    assert put_resp.json()["is_bot_active_global"] is True
    assert BotSchedule.objects.filter(tenant=tenant).count() == 7
    monday = BotSchedule.objects.get(tenant=tenant, day_of_week=0)
    assert monday.is_active is True
    assert monday.start_time == time(8, 0)


@pytest.mark.django_db
def test_bot_schedule_patch_global_active(api_client):
    tenant = TenantFactory(is_bot_active_global=True)
    user = UserFactory(tenant=tenant, email="schedule-global@example.com")
    _auth(api_client, user)
    url = reverse("settings-bot-schedule")

    resp = api_client.patch(url, {"is_bot_active_global": False}, format="json")
    assert resp.status_code == 200
    assert resp.json()["is_bot_active_global"] is False
    tenant.refresh_from_db()
    assert tenant.is_bot_active_global is False

    resp = api_client.patch(url, {"is_bot_active_global": True}, format="json")
    assert resp.status_code == 200
    assert resp.json()["is_bot_active_global"] is True


@pytest.mark.django_db
def test_bot_schedule_put_rejects_invalid_window(api_client):
    tenant = TenantFactory()
    user = UserFactory(tenant=tenant, email="schedule-bad@example.com")
    _auth(api_client, user)
    days = [
        {
            "day_of_week": i,
            "is_active": i == 0,
            "start_time": "18:00:00" if i == 0 else "09:00:00",
            "end_time": "09:00:00" if i == 0 else "18:00:00",
        }
        for i in range(7)
    ]
    resp = api_client.put(reverse("settings-bot-schedule"), {"days": days}, format="json")
    assert resp.status_code == 400


@pytest.mark.django_db
def test_webhook_mutes_bot_during_business_hours():
    tenant = TenantFactory()
    instance = WhatsappInstanceFactory(tenant=tenant, webhook_secret="sec")
    market = MarketFactory(tenant=tenant)
    resident = ResidentFactory(
        tenant=tenant,
        market=market,
        phone_number="5511999887766",
    )
    ChatSessionFactory(
        tenant=tenant,
        phone_number=resident.phone_number,
        state=ChatSession.State.IDLE,
        is_bot_active=True,
    )
    for day in range(7):
        BotSchedule.objects.create(
            tenant=tenant,
            day_of_week=day,
            is_active=True,
            start_time=time(9, 0),
            end_time=time(18, 0),
        )

    event = EvolutionWebhookEvent(
        event_type="MESSAGE",
        instance_key=instance.instance_name,
        connection_state="",
        remote_jid=f"{resident.phone_number}@s.whatsapp.net",
        message_id="msg-schedule",
        from_me=False,
        message_text="oi",
        message_kind="text",
    )

    with (
        mock.patch(
            "apps.chatbot.services.bot_schedule.should_bot_auto_reply",
            return_value=False,
        ),
        mock.patch(
            "apps.integrations.services.webhook_handlers.process_cart_flow",
        ) as cart_flow,
        mock.patch(
            "apps.integrations.services.webhook_handlers.run_chatbot_flow",
        ) as chatbot_flow,
        mock.patch(
            "apps.chatbot.services.human_handover.ensure_bot_active_or_timeout",
            return_value=True,
        ),
    ):
        handle_evolution_webhook(event, instance)

    cart_flow.assert_not_called()
    chatbot_flow.assert_not_called()


@pytest.mark.django_db
def test_webhook_mutes_bot_when_global_switch_off():
    """Chave geral False tem prioridade sobre horário (bot deveria falar fora do expediente)."""
    tenant = TenantFactory(is_bot_active_global=False)
    instance = WhatsappInstanceFactory(tenant=tenant, webhook_secret="sec")
    market = MarketFactory(tenant=tenant)
    resident = ResidentFactory(
        tenant=tenant,
        market=market,
        phone_number="5511999887766",
    )
    ChatSessionFactory(
        tenant=tenant,
        phone_number=resident.phone_number,
        state=ChatSession.State.IDLE,
        is_bot_active=True,
    )
    # Folga / sem expediente → schedule permitiria bot, mas chave geral bloqueia
    for day in range(7):
        BotSchedule.objects.create(
            tenant=tenant,
            day_of_week=day,
            is_active=False,
            start_time=time(9, 0),
            end_time=time(18, 0),
        )

    event = EvolutionWebhookEvent(
        event_type="MESSAGE",
        instance_key=instance.instance_name,
        connection_state="",
        remote_jid=f"{resident.phone_number}@s.whatsapp.net",
        message_id="msg-global-off",
        from_me=False,
        message_text="oi",
        message_kind="text",
    )

    with (
        mock.patch(
            "apps.chatbot.services.bot_schedule.should_bot_auto_reply",
            return_value=True,
        ) as schedule_check,
        mock.patch(
            "apps.integrations.services.webhook_handlers.process_cart_flow",
        ) as cart_flow,
        mock.patch(
            "apps.integrations.services.webhook_handlers.run_chatbot_flow",
        ) as chatbot_flow,
        mock.patch(
            "apps.chatbot.services.human_handover.ensure_bot_active_or_timeout",
            return_value=True,
        ) as handover,
    ):
        handle_evolution_webhook(event, instance)

    cart_flow.assert_not_called()
    chatbot_flow.assert_not_called()
    # Chave geral corta antes de schedule/handover
    schedule_check.assert_not_called()
    handover.assert_not_called()

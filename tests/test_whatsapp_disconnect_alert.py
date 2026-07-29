from __future__ import annotations

from unittest import mock

import pytest
from django.core import mail
from django.core.cache import cache
from rest_framework.test import APIClient

from apps.core.emails import WHATSAPP_DISCONNECTED_SUBJECT
from apps.integrations.models import WhatsappInstance
from apps.integrations.services.provisioning import mark_whatsapp_session_disconnected
from apps.integrations.services.webhook_handlers import handle_evolution_webhook
from apps.integrations.services.webhook_parser import EvolutionWebhookEvent
from apps.integrations.services.whatsapp_connection_alert import (
    on_whatsapp_connected,
    on_whatsapp_disconnected,
    send_disconnect_email_if_still_down,
)
from apps.tenants.context import tenant_scope
from tests.factories import TenantFactory, UserFactory, WhatsappInstanceFactory


@pytest.fixture(autouse=True)
def _clear_cache():
    cache.clear()
    yield
    cache.clear()


@pytest.mark.django_db
def test_disconnected_webhook_sets_tenant_flag_false():
    tenant = TenantFactory(is_whatsapp_connected=True)
    instance = WhatsappInstanceFactory(
        tenant=tenant,
        connection_status=WhatsappInstance.ConnectionStatus.OPEN,
    )
    event = EvolutionWebhookEvent(
        event_type="DISCONNECTED",
        instance_key=instance.instance_name,
        connection_state="close",
        remote_jid="",
        message_id="",
        from_me=False,
        message_text="",
        message_kind="",
    )

    with mock.patch(
        "apps.integrations.services.whatsapp_connection_alert.threading.Timer",
    ) as timer_cls:
        timer_cls.return_value = mock.Mock()
        with tenant_scope(tenant.id):
            handle_evolution_webhook(event, instance)

    tenant.refresh_from_db()
    instance.refresh_from_db()
    assert tenant.is_whatsapp_connected is False
    assert instance.connection_status == WhatsappInstance.ConnectionStatus.CLOSE
    timer_cls.assert_called()


@pytest.mark.django_db
def test_connected_webhook_sets_tenant_flag_true_and_cancels_email():
    tenant = TenantFactory(is_whatsapp_connected=False)
    instance = WhatsappInstanceFactory(
        tenant=tenant,
        connection_status=WhatsappInstance.ConnectionStatus.CLOSE,
    )
    cache.set(f"wa_disconnect_email:{tenant.id}", "old-token", timeout=180)

    event = EvolutionWebhookEvent(
        event_type="CONNECTED",
        instance_key=instance.instance_name,
        connection_state="open",
        remote_jid="",
        message_id="",
        from_me=False,
        message_text="",
        message_kind="",
    )

    with mock.patch(
        "apps.integrations.services.webhook_handlers.sync_profile_avatar_from_evolution",
    ):
        with tenant_scope(tenant.id):
            handle_evolution_webhook(event, instance)

    tenant.refresh_from_db()
    assert tenant.is_whatsapp_connected is True
    assert cache.get(f"wa_disconnect_email:{tenant.id}") is None


@pytest.mark.django_db
def test_reconnect_before_delay_skips_email():
    tenant = TenantFactory(is_whatsapp_connected=True)
    UserFactory(tenant=tenant, email="admin@example.com", is_tenant_admin=True)
    instance = WhatsappInstanceFactory(
        tenant=tenant,
        connection_status=WhatsappInstance.ConnectionStatus.OPEN,
    )
    mail.outbox.clear()

    captured: list = []

    def fake_timer(delay, fn, args=None, kwargs=None):
        t = mock.Mock()
        captured.append((delay, fn, args or (), kwargs or {}))
        t.start = mock.Mock()
        return t

    with mock.patch(
        "apps.integrations.services.whatsapp_connection_alert.threading.Timer",
        side_effect=fake_timer,
    ):
        on_whatsapp_disconnected(instance)

    assert captured
    delay, fn, args, _kwargs = captured[0]
    assert delay == 120
    assert fn is send_disconnect_email_if_still_down

    on_whatsapp_connected(instance)
    fn(*args)

    assert len(mail.outbox) == 0
    tenant.refresh_from_db()
    assert tenant.is_whatsapp_connected is True


@pytest.mark.django_db
def test_still_disconnected_after_delay_sends_urgent_email():
    tenant = TenantFactory(is_whatsapp_connected=True)
    UserFactory(tenant=tenant, email="owner@loja.com", first_name="Ana", is_tenant_admin=True)
    instance = WhatsappInstanceFactory(
        tenant=tenant,
        connection_status=WhatsappInstance.ConnectionStatus.OPEN,
    )
    mail.outbox.clear()

    captured: list = []

    def fake_timer(delay, fn, args=None, kwargs=None):
        t = mock.Mock()
        captured.append((fn, args or ()))
        t.start = mock.Mock()
        return t

    with mock.patch(
        "apps.integrations.services.whatsapp_connection_alert.threading.Timer",
        side_effect=fake_timer,
    ):
        mark_whatsapp_session_disconnected(instance)

    tenant.refresh_from_db()
    assert tenant.is_whatsapp_connected is False
    instance.refresh_from_db()
    assert instance.connection_status == WhatsappInstance.ConnectionStatus.CLOSE

    fn, args = captured[0]
    fn(*args)

    assert len(mail.outbox) == 1
    assert mail.outbox[0].subject == WHATSAPP_DISCONNECTED_SUBJECT
    body = mail.outbox[0].body
    assert "perdendo vendas" in body
    assert "QR Code" in body


@pytest.mark.django_db
def test_disconnect_email_sent_only_once_within_hour():
    tenant = TenantFactory(is_whatsapp_connected=False)
    UserFactory(tenant=tenant, email="owner@loja.com", is_tenant_admin=True)
    instance = WhatsappInstanceFactory(
        tenant=tenant,
        connection_status=WhatsappInstance.ConnectionStatus.CLOSE,
    )
    mail.outbox.clear()

    token = "tok-1"
    cache.set(f"wa_disconnect_email:{tenant.id}", token, timeout=180)
    send_disconnect_email_if_still_down(tenant.id, instance.pk, token)
    assert len(mail.outbox) == 1

    cache.set(f"wa_disconnect_email:{tenant.id}", "tok-2", timeout=180)
    send_disconnect_email_if_still_down(tenant.id, instance.pk, "tok-2")
    assert len(mail.outbox) == 1


@pytest.mark.django_db
def test_me_exposes_whatsapp_connection_flags(api_client: APIClient):
    tenant = TenantFactory(is_whatsapp_connected=False)
    user = UserFactory(tenant=tenant, is_tenant_admin=True)
    WhatsappInstanceFactory(
        tenant=tenant,
        connection_status=WhatsappInstance.ConnectionStatus.CLOSE,
    )
    api_client.force_authenticate(user=user)
    response = api_client.get("/api/auth/me/")
    assert response.status_code == 200
    assert response.data["is_whatsapp_connected"] is False
    assert response.data["has_whatsapp_instance"] is True
    assert response.data["is_tenant_admin"] is True

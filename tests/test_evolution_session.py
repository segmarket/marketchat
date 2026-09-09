"""Guardas de QR/connect após autenticação Evolution."""

from __future__ import annotations

from io import BytesIO
from unittest.mock import MagicMock, patch
import urllib.error

import pytest
from django.core.cache import cache
from django.urls import reverse
from rest_framework_simplejwt.tokens import RefreshToken

from apps.integrations.models import WhatsappInstance
from apps.integrations.services.evolution_client import EvolutionClient
from apps.integrations.services.evolution_session import (
    EvolutionOpLock,
    apply_authenticated_session,
    block_qr_after_connected,
    get_cached_pairing_qr,
    parse_remote_session,
    try_begin_connect_flight,
)
from apps.integrations.services.provisioning import (
    provision_whatsapp_instance,
    refresh_qrcode,
    sync_connection_status,
)
from apps.integrations.services.restart import restart_whatsapp_instance
from apps.integrations.services.webhook_handlers import handle_evolution_webhook
from apps.integrations.services.webhook_parser import EvolutionWebhookEvent
from tests.factories import TenantFactory, UserFactory, WhatsappInstanceFactory


@pytest.fixture(autouse=True)
def _clear_cache():
    cache.clear()
    yield
    cache.clear()


def _http_error(url: str, code: int, body: bytes) -> urllib.error.HTTPError:
    exc = urllib.error.HTTPError(url, code, "Bad Request", {}, BytesIO(body))
    exc._body_preview = body
    return exc


def test_parse_remote_session_logged_in_connected():
    session = parse_remote_session(
        {"connected": True, "loggedIn": True, "data": {"state": "open"}}
    )
    assert session.logged_in is True
    assert session.connected is True
    assert session.forbids_qr is True
    assert session.is_fully_connected is True


def test_parse_remote_session_logged_in_not_connected():
    session = parse_remote_session({"loggedIn": True, "connected": False})
    assert session.logged_in is True
    assert session.connected is False
    assert session.forbids_qr is True
    assert session.is_fully_connected is False


def test_parse_remote_session_connecting_allows_qr():
    session = parse_remote_session({"data": {"state": "connecting"}})
    assert session.logged_in is False
    assert session.forbids_qr is False


def test_fetch_qrcode_already_logged_in_no_retry():
    client = EvolutionClient(base_url="http://evo.test", global_api_key="global")
    exc = _http_error(
        "http://evo.test/instance/qr",
        400,
        b'{"error":"session already logged in"}',
    )
    with patch.object(client, "_request", side_effect=exc) as mock_req:
        result = client.fetch_qrcode(instance_api_key="tok", retries=3, retry_delay=0.01)
    assert result["connected"] is True
    assert mock_req.call_count == 1


@pytest.mark.django_db
def test_refresh_qrcode_skips_when_local_open():
    inst = WhatsappInstanceFactory(
        is_active=True,
        connection_status=WhatsappInstance.ConnectionStatus.OPEN,
    )
    mock_client = MagicMock()
    result = refresh_qrcode(inst, client=mock_client, skip_status_sync=True)
    assert result["connected"] is True
    assert result["qrcode_image"] == ""
    mock_client.fetch_qrcode.assert_not_called()
    mock_client.connection_state.assert_not_called()


@pytest.mark.django_db
def test_refresh_qrcode_skips_when_remote_logged_in():
    inst = WhatsappInstanceFactory(
        is_active=True,
        connection_status=WhatsappInstance.ConnectionStatus.CONNECTING,
    )
    mock_client = MagicMock()
    mock_client.fetch_remote_instance.return_value = {"name": inst.instance_name}
    mock_client.connection_state.return_value = {
        "loggedIn": True,
        "connected": True,
        "data": {"state": "open"},
    }
    result = refresh_qrcode(inst, client=mock_client, skip_status_sync=True)
    assert result["connected"] is True
    mock_client.fetch_qrcode.assert_not_called()
    inst.refresh_from_db()
    assert inst.connection_status == WhatsappInstance.ConnectionStatus.OPEN


@pytest.mark.django_db
def test_refresh_qrcode_skips_logged_in_disconnected():
    inst = WhatsappInstanceFactory(
        is_active=True,
        connection_status=WhatsappInstance.ConnectionStatus.CONNECTING,
    )
    mock_client = MagicMock()
    mock_client.fetch_remote_instance.return_value = {"name": inst.instance_name}
    mock_client.connection_state.return_value = {"loggedIn": True, "connected": False}
    result = refresh_qrcode(inst, client=mock_client, skip_status_sync=True)
    assert result["connected"] is True
    mock_client.fetch_qrcode.assert_not_called()


@pytest.mark.django_db
def test_refresh_qrcode_skips_when_lock_held():
    inst = WhatsappInstanceFactory(
        is_active=True,
        connection_status=WhatsappInstance.ConnectionStatus.CONNECTING,
    )
    mock_client = MagicMock()
    mock_client.fetch_remote_instance.return_value = {"name": inst.instance_name}
    mock_client.connection_state.return_value = {"data": {"state": "connecting"}}
    lock = EvolutionOpLock(inst)
    assert lock.acquire() is True
    try:
        result = refresh_qrcode(inst, client=mock_client, skip_status_sync=True)
    finally:
        lock.release()
    assert result.get("qr_pending") is True
    mock_client.fetch_qrcode.assert_not_called()


@pytest.mark.django_db
@patch("apps.integrations.services.webhook_handlers.sync_profile_avatar_from_evolution")
def test_refresh_qrcode_skips_after_connected_webhook(mock_avatar):
    del mock_avatar
    inst = WhatsappInstanceFactory(
        is_active=True,
        connection_status=WhatsappInstance.ConnectionStatus.CONNECTING,
        webhook_secret="sec",
    )
    handle_evolution_webhook(
        EvolutionWebhookEvent(
            event_type="CONNECTED",
            instance_key=inst.instance_name,
            connection_state="open",
            remote_jid="",
            message_id="",
            from_me=False,
        ),
        inst,
    )
    inst.refresh_from_db()
    mock_client = MagicMock()
    result = refresh_qrcode(inst, client=mock_client, skip_status_sync=True)
    assert result["connected"] is True
    mock_client.fetch_qrcode.assert_not_called()


@pytest.mark.django_db
@patch("apps.integrations.services.provisioning.EvolutionClient")
def test_provision_does_not_call_get_instance_qr(mock_client_cls):
    tenant = TenantFactory(slug="qr-once")
    mock_client = MagicMock()
    mock_client_cls.return_value = mock_client
    mock_client.create_instance_safe.return_value = {}
    mock_client.connect_instance.return_value = {
        "data": {"Qrcode": f"data:image/png;base64,{'A' * 120}"},
    }
    mock_client.connection_state.return_value = {"data": {"state": "connecting"}}
    result = provision_whatsapp_instance(tenant, client=mock_client)
    assert result["qrcode_image"].startswith("data:image")
    mock_client.connect_instance.assert_called_once()
    mock_client.fetch_qrcode.assert_not_called()


@pytest.mark.django_db
@patch("apps.integrations.services.provisioning.EvolutionClient")
def test_provision_skips_qr_when_already_logged_in(mock_client_cls):
    tenant = TenantFactory(slug="already-in")
    mock_client = MagicMock()
    mock_client_cls.return_value = mock_client
    mock_client.create_instance_safe.return_value = {}
    mock_client.connect_instance.return_value = {}
    mock_client.connection_state.return_value = {"loggedIn": True, "connected": True}
    result = provision_whatsapp_instance(tenant, client=mock_client)
    assert result["qrcode_image"] == ""
    mock_client.fetch_qrcode.assert_not_called()
    assert result["instance"].connection_status == WhatsappInstance.ConnectionStatus.OPEN


@pytest.mark.django_db
def test_restart_open_skips_connect_and_qr():
    inst = WhatsappInstanceFactory(
        is_active=True,
        connection_status=WhatsappInstance.ConnectionStatus.OPEN,
        webhook_url="http://localhost/api/integrations/webhooks/evolution/?secret=test",
    )
    mock_client = MagicMock()
    mock_client.connection_state.return_value = {
        "loggedIn": True,
        "connected": True,
        "data": {"state": "open"},
    }
    out, qr = restart_whatsapp_instance(inst, client=mock_client)
    assert qr == ""
    mock_client.connect_instance.assert_not_called()
    mock_client.reconnect_instance.assert_not_called()
    mock_client.fetch_qrcode.assert_not_called()
    mock_client.create_instance_safe.assert_not_called()
    assert out.connection_status == WhatsappInstance.ConnectionStatus.OPEN


@pytest.mark.django_db
def test_sync_promotes_connecting_when_logged_in():
    inst = WhatsappInstanceFactory(
        is_active=True,
        connection_status=WhatsappInstance.ConnectionStatus.CONNECTING,
    )
    mock_client = MagicMock()
    mock_client.connection_state.return_value = {
        "loggedIn": True,
        "connected": True,
        "data": {"state": "open"},
    }
    status = sync_connection_status(inst, client=mock_client)
    assert status == WhatsappInstance.ConnectionStatus.OPEN
    inst.refresh_from_db()
    assert inst.connection_status == WhatsappInstance.ConnectionStatus.OPEN


@pytest.mark.django_db
@patch("apps.integrations.services.instance_dashboard.EvolutionClient")
@patch("apps.integrations.services.provisioning.EvolutionClient")
def test_qrcode_view_zero_qr_calls_when_open(mock_prov_cls, mock_dash_cls, api_client):
    tenant = TenantFactory()
    user = UserFactory(tenant=tenant, email="wa-qr-open@example.com")
    WhatsappInstanceFactory(
        tenant=tenant,
        is_active=True,
        connection_status=WhatsappInstance.ConnectionStatus.OPEN,
    )
    mock_client = MagicMock()
    mock_prov_cls.return_value = mock_client
    mock_dash_cls.return_value = mock_client
    mock_client.check_evolution_health.return_value = "ok"

    url = reverse("integrations-whatsapp-qrcode")
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(user).access_token}")
    response = api_client.get(url)
    assert response.status_code == 200
    assert response.json()["connected"] is True
    mock_client.fetch_qrcode.assert_not_called()


@pytest.mark.django_db
@patch("apps.integrations.services.instance_dashboard.EvolutionClient")
@patch("apps.integrations.services.provisioning.EvolutionClient")
def test_status_view_promotes_logged_in_during_connecting(
    mock_prov_cls, mock_dash_cls, api_client
):
    tenant = TenantFactory()
    user = UserFactory(tenant=tenant, email="wa-status-li@example.com")
    WhatsappInstanceFactory(
        tenant=tenant,
        is_active=True,
        connection_status=WhatsappInstance.ConnectionStatus.CONNECTING,
    )
    mock_client = MagicMock()
    mock_prov_cls.return_value = mock_client
    mock_dash_cls.return_value = mock_client
    mock_client.check_evolution_health.return_value = "ok"
    mock_client.fetch_remote_instance.return_value = {"connected": True}
    mock_client.connection_state.return_value = {
        "loggedIn": True,
        "connected": True,
        "data": {"state": "open"},
    }

    url = reverse("integrations-whatsapp-status")
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(user).access_token}")
    response = api_client.get(url)
    assert response.status_code == 200
    data = response.json()
    assert data["connected"] is True
    assert data["connection_status"] == "open"
    mock_client.fetch_qrcode.assert_not_called()


@pytest.mark.django_db
def test_apply_authenticated_session_is_idempotent():
    inst = WhatsappInstanceFactory(
        is_active=True,
        connection_status=WhatsappInstance.ConnectionStatus.OPEN,
    )
    apply_authenticated_session(inst, reason="connected")
    block_qr_after_connected(inst, reason="connected")
    mock_client = MagicMock()
    result = refresh_qrcode(inst, client=mock_client, skip_status_sync=True)
    assert result["connected"] is True
    mock_client.fetch_qrcode.assert_not_called()


@pytest.mark.django_db
@patch("apps.integrations.services.webhook_handlers.sync_profile_avatar_from_evolution")
def test_qrcode_webhook_caches_image_without_get_qr(mock_avatar):
    del mock_avatar
    inst = WhatsappInstanceFactory(
        is_active=True,
        connection_status=WhatsappInstance.ConnectionStatus.CONNECTING,
    )
    image = f"data:image/png;base64,{'W' * 120}"
    handle_evolution_webhook(
        EvolutionWebhookEvent(
            event_type="QRCODE",
            instance_key=inst.instance_name,
            connection_state="",
            remote_jid="",
            message_id="",
            from_me=False,
            raw_message={"Qrcode": image},
        ),
        inst,
    )
    assert get_cached_pairing_qr(inst).startswith("data:image")
    mock_client = MagicMock()
    result = refresh_qrcode(inst, client=mock_client)
    assert result["qrcode_image"].startswith("data:image")
    mock_client.fetch_qrcode.assert_not_called()
    mock_client.connect_instance.assert_not_called()


@pytest.mark.django_db
@patch("apps.integrations.services.webhook_handlers.sync_profile_avatar_from_evolution")
@patch("apps.integrations.services.provisioning.EvolutionClient")
def test_connect_then_simultaneous_qr_starts_exactly_one_runtime(
    mock_client_cls,
    mock_avatar,
):
    """Regressão PR #145: connect + GET /qr simultâneo não cria 2 websockets."""
    del mock_avatar
    tenant = TenantFactory(slug="one-runtime")
    mock_client = MagicMock()
    mock_client_cls.return_value = mock_client
    mock_client.create_instance_safe.return_value = {}
    mock_client.connect_instance.return_value = {}
    mock_client.connection_state.return_value = {"data": {"state": "connecting"}}

    result = provision_whatsapp_instance(tenant, client=mock_client)
    instance = result["instance"]
    mock_client.connect_instance.assert_called_once()
    mock_client.fetch_qrcode.assert_not_called()

    image = f"data:image/png;base64,{'Q' * 120}"
    handle_evolution_webhook(
        EvolutionWebhookEvent(
            event_type="QRCODE",
            instance_key=instance.instance_name,
            connection_state="",
            remote_jid="",
            message_id="",
            from_me=False,
            raw_message={"base64": image},
        ),
        instance,
    )
    qr1 = refresh_qrcode(instance, client=mock_client)
    qr2 = refresh_qrcode(instance, client=mock_client)
    assert qr1["qrcode_image"]
    assert qr2["qrcode_image"] == qr1["qrcode_image"]
    mock_client.fetch_qrcode.assert_not_called()

    handle_evolution_webhook(
        EvolutionWebhookEvent(
            event_type="PAIRSUCCESS",
            instance_key=instance.instance_name,
            connection_state="open",
            remote_jid="",
            message_id="",
            from_me=False,
        ),
        instance,
    )
    instance.refresh_from_db()
    assert instance.connection_status == WhatsappInstance.ConnectionStatus.OPEN
    assert get_cached_pairing_qr(instance) == ""
    after = refresh_qrcode(instance, client=mock_client)
    assert after["connected"] is True
    mock_client.fetch_qrcode.assert_not_called()
    assert mock_client.connect_instance.call_count == 1

    # Analogia ao QR timeout do Evolution (~120s): após PairSuccess o backend
    # não dispara GET /instance/qr, então um runtime órfão não é alimentado.
    for _ in range(8):
        later = refresh_qrcode(instance, client=mock_client)
        assert later["connected"] is True
        assert later["qrcode_image"] == ""
    mock_client.fetch_qrcode.assert_not_called()
    mock_client.connect_instance.assert_called_once()


def test_fetch_qrcode_after_connect_never_hits_instance_qr():
    client = EvolutionClient(base_url="http://evo.test", global_api_key="global")
    with patch.object(client, "fetch_qrcode") as mock_qr:
        with patch.object(client, "connection_state") as mock_status:
            out = client._fetch_qrcode_after_connect(
                instance_api_key="tok",
                connect_payload={"message": "success"},
            )
    assert out.get("qr_pending") is True
    mock_qr.assert_not_called()
    mock_status.assert_not_called()


@pytest.mark.django_db
def test_connect_flight_rejects_second_connect():
    inst = WhatsappInstanceFactory(instance_id="same-runtime-id")
    assert try_begin_connect_flight(inst.instance_id) is True
    assert try_begin_connect_flight(inst.instance_id) is False


@pytest.mark.django_db
@patch("apps.integrations.services.instance_dashboard.EvolutionClient")
@patch("apps.integrations.services.provisioning.EvolutionClient")
@patch("apps.integrations.services.webhook_handlers.sync_profile_avatar_from_evolution")
def test_http_connect_and_qrcode_endpoint_share_single_runtime(
    mock_avatar,
    mock_prov_cls,
    mock_dash_cls,
    api_client,
):
    del mock_avatar
    tenant = TenantFactory(slug="http-runtime")
    user = UserFactory(tenant=tenant, email="wa-runtime@example.com")
    mock_client = MagicMock()
    mock_prov_cls.return_value = mock_client
    mock_dash_cls.return_value = mock_client
    mock_client.create_instance_safe.return_value = {}
    mock_client.connect_instance.return_value = {}
    mock_client.connection_state.return_value = {"data": {"state": "connecting"}}
    mock_client.check_evolution_health.return_value = "ok"
    mock_client.fetch_remote_instance.return_value = {"connected": False}

    api_client.credentials(
        HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(user).access_token}"
    )
    provision = api_client.post(reverse("integrations-whatsapp-provision"), {}, format="json")
    assert provision.status_code == 201
    mock_client.connect_instance.assert_called_once()
    mock_client.fetch_qrcode.assert_not_called()

    inst = WhatsappInstance.objects.get(tenant=tenant)
    image = f"data:image/png;base64,{'H' * 120}"
    handle_evolution_webhook(
        EvolutionWebhookEvent(
            event_type="QRCODE",
            instance_key=inst.instance_name,
            connection_state="",
            remote_jid="",
            message_id="",
            from_me=False,
            raw_message={"Qrcode": image},
        ),
        inst,
    )
    qr_response = api_client.get(reverse("integrations-whatsapp-qrcode"))
    status_response = api_client.get(reverse("integrations-whatsapp-status"))
    assert qr_response.status_code == 200
    assert status_response.status_code == 200
    assert qr_response.json()["qrcode_image"].startswith("data:image")
    assert status_response.json()["qrcode_image"].startswith("data:image")
    mock_client.fetch_qrcode.assert_not_called()
    mock_client.connect_instance.assert_called_once()

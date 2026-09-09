import urllib.error
from datetime import timedelta
from unittest.mock import MagicMock, patch

import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework_simplejwt.tokens import RefreshToken

from apps.integrations.models import WhatsappInstance
from apps.integrations.services.provisioning import (
    WhatsappAlreadyProvisionedError,
    mark_whatsapp_session_disconnected,
    provision_whatsapp_instance,
    remote_instance_exists,
    sync_connection_status,
)
from tests.factories import ResidentFactory, TenantFactory, UserFactory, WhatsappInstanceFactory


@pytest.mark.django_db
def test_whatsapp_get_no_instance(api_client):
    tenant = TenantFactory()
    user = UserFactory(tenant=tenant, email="wa-empty@example.com")
    url = reverse("integrations-whatsapp")
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(user).access_token}")
    response = api_client.get(url)
    assert response.status_code == 200
    data = response.json()
    assert data["has_instance"] is False
    assert data["evolution_api_status"] in ("ok", "error")
    assert data["webhook_status"] == "unknown"


def _mock_evolution_client() -> MagicMock:
    mock_client = MagicMock()
    mock_client.connection_state.return_value = {"data": {"state": "connecting"}}
    mock_client.fetch_remote_instance.return_value = {"connected": False}
    mock_client.check_evolution_health.return_value = "ok"
    return mock_client


@pytest.mark.django_db
@patch("apps.integrations.services.instance_dashboard.EvolutionClient")
@patch("apps.integrations.services.provisioning.EvolutionClient")
def test_whatsapp_provision_success(mock_prov_cls, mock_dash_cls, api_client):
    tenant = TenantFactory(slug="acme-corp")
    user = UserFactory(tenant=tenant, email="wa-admin@example.com")
    mock_client = _mock_evolution_client()
    mock_prov_cls.return_value = mock_client
    mock_dash_cls.return_value = mock_client
    mock_client.create_instance_safe.return_value = {"ok": True}
    mock_client.connect_instance.return_value = {
        "data": {"Qrcode": f"data:image/png;base64,{'A' * 120}"},
    }

    url = reverse("integrations-whatsapp-provision")
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(user).access_token}")
    response = api_client.post(url, {}, format="json")
    assert response.status_code == 201
    data = response.json()
    assert data["has_instance"] is True
    assert data["instance_name"] == "mc-acme-corp"
    assert data["qrcode_image"].startswith("data:image")
    assert WhatsappInstance.objects.filter(tenant=tenant, is_active=True).count() == 1


@pytest.mark.django_db
@patch("apps.integrations.services.provisioning.EvolutionClient")
def test_whatsapp_provision_rollback_on_connect_failure(mock_client_cls, api_client):
    tenant = TenantFactory()
    user = UserFactory(tenant=tenant, email="wa-fail@example.com")
    mock_client = MagicMock()
    mock_client_cls.return_value = mock_client
    mock_client.create_instance_safe.return_value = {"ok": True}
    mock_client.connect_instance.side_effect = RuntimeError("connect failed")

    url = reverse("integrations-whatsapp-provision")
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(user).access_token}")
    response = api_client.post(url, {}, format="json")
    assert response.status_code == 502
    assert mock_client.delete_instance.call_count >= 1
    assert WhatsappInstance.objects.filter(tenant=tenant).count() == 0


@pytest.mark.django_db
@patch("apps.integrations.services.instance_dashboard.EvolutionClient")
@patch("apps.integrations.services.provisioning.EvolutionClient")
def test_whatsapp_provision_after_disconnect_reuses_row(mock_prov_cls, mock_dash_cls, api_client):
    tenant = TenantFactory(slug="reconnect-co")
    user = UserFactory(tenant=tenant, email="wa-reconnect@example.com")
    WhatsappInstanceFactory(
        tenant=tenant,
        is_active=False,
        instance_id="old-evolution-id",
        instance_name="mc-old",
    )
    mock_client = _mock_evolution_client()
    mock_prov_cls.return_value = mock_client
    mock_dash_cls.return_value = mock_client
    mock_client.create_instance_safe.return_value = {"ok": True}
    mock_client.connect_instance.return_value = {"ok": True}
    mock_client.fetch_qrcode.return_value = {"data": {"Qrcode": f"data:image/png;base64,{'B' * 120}"}}

    url = reverse("integrations-whatsapp-provision")
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(user).access_token}")
    response = api_client.post(url, {}, format="json")
    assert response.status_code == 201
    assert WhatsappInstance.all_objects.filter(tenant=tenant).count() == 1
    inst = WhatsappInstance.all_objects.get(tenant=tenant)
    assert inst.is_active is True
    assert inst.instance_name == "mc-reconnect-co"
    mock_client.delete_instance.assert_any_call(
        instance_name="mc-old",
        instance_id="old-evolution-id",
    )


@pytest.mark.django_db
@patch("apps.integrations.services.provisioning.EvolutionClient")
def test_whatsapp_provision_conflict_when_active(mock_client_cls, api_client):
    tenant = TenantFactory()
    user = UserFactory(tenant=tenant, email="wa-dup@example.com")
    WhatsappInstanceFactory(
        tenant=tenant,
        is_active=True,
        connection_status=WhatsappInstance.ConnectionStatus.OPEN,
    )
    mock_client = MagicMock()
    mock_client_cls.return_value = mock_client
    mock_client.fetch_remote_instance.return_value = {"instanceName": "mc-test-1"}

    url = reverse("integrations-whatsapp-provision")
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(user).access_token}")
    response = api_client.post(url, {}, format="json")
    assert response.status_code == 409


@pytest.mark.django_db
def test_remote_instance_exists_treats_503_as_still_present():
    tenant = TenantFactory()
    inst = WhatsappInstanceFactory(tenant=tenant, is_active=True, instance_name="mc-503-unit")
    mock_client = MagicMock()
    mock_client.fetch_remote_instance.side_effect = urllib.error.HTTPError(
        "http://localhost:8080/instance/all",
        503,
        "Service Unavailable",
        {},
        None,
    )
    assert remote_instance_exists(inst, client=mock_client) is True


@pytest.mark.django_db
@patch(
    "apps.integrations.services.provisioning.remote_instance_exists",
    return_value=True,
)
@patch("apps.integrations.services.provisioning.EvolutionClient")
@patch("apps.integrations.services.instance_dashboard.EvolutionClient")
def test_whatsapp_get_survives_evolution_http_503(
    mock_dash_cls,
    mock_prov_cls,
    _mock_exists,
    api_client,
):
    tenant = TenantFactory()
    user = UserFactory(tenant=tenant, email="wa-evo-503@example.com")
    WhatsappInstanceFactory(
        tenant=tenant,
        is_active=True,
        instance_name="mc-evo-503",
        connection_status=WhatsappInstance.ConnectionStatus.OPEN,
    )
    mock_client = MagicMock()
    mock_dash_cls.return_value = mock_client
    mock_prov_cls.return_value = mock_client
    mock_client.check_evolution_health.return_value = "error"
    mock_client.connection_state.return_value = {"data": {"state": "open"}}

    url = reverse("integrations-whatsapp")
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(user).access_token}")
    response = api_client.get(url)

    assert response.status_code == 200
    assert response.json()["has_instance"] is True
    assert response.json()["evolution_api_status"] == "error"


@pytest.mark.django_db
@patch("apps.integrations.services.instance_dashboard.EvolutionClient")
@patch("apps.integrations.services.provisioning.EvolutionClient")
def test_whatsapp_get_survives_evolution_unreachable(
    mock_prov_cls,
    mock_dash_cls,
    api_client,
):
    tenant = TenantFactory()
    user = UserFactory(tenant=tenant, email="wa-evo-down@example.com")
    WhatsappInstanceFactory(
        tenant=tenant,
        is_active=True,
        instance_name="mc-evo-down",
        connection_status=WhatsappInstance.ConnectionStatus.OPEN,
    )
    mock_client = MagicMock()
    mock_prov_cls.return_value = mock_client
    mock_dash_cls.return_value = mock_client
    mock_client.fetch_remote_instance.side_effect = urllib.error.URLError(
        "Connection refused",
    )
    mock_client.check_evolution_health.return_value = "error"

    url = reverse("integrations-whatsapp")
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(user).access_token}")
    response = api_client.get(url)

    assert response.status_code == 200
    assert response.json()["has_instance"] is True
    assert response.json()["evolution_api_status"] == "error"


@pytest.mark.django_db
@patch("apps.integrations.services.provisioning.EvolutionClient")
def test_whatsapp_get_reconciles_missing_remote(mock_client_cls, api_client):
    tenant = TenantFactory()
    user = UserFactory(tenant=tenant, email="wa-orphan@example.com")
    inst = WhatsappInstanceFactory(
        tenant=tenant,
        is_active=True,
        connection_status=WhatsappInstance.ConnectionStatus.CONNECTING,
    )
    mock_client = MagicMock()
    mock_client_cls.return_value = mock_client
    mock_client.fetch_remote_instance.return_value = None

    url = reverse("integrations-whatsapp")
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(user).access_token}")
    response = api_client.get(url)

    assert response.status_code == 200
    assert response.json()["has_instance"] is True
    inst.refresh_from_db()
    assert inst.is_active is False
    assert inst.connection_status == WhatsappInstance.ConnectionStatus.CLOSE


@pytest.mark.django_db
@patch("apps.integrations.services.provisioning.EvolutionClient")
def test_whatsapp_status_no_502_when_remote_missing(mock_client_cls, api_client):
    tenant = TenantFactory()
    user = UserFactory(tenant=tenant, email="wa-status-orphan@example.com")
    WhatsappInstanceFactory(
        tenant=tenant,
        is_active=True,
        connection_status=WhatsappInstance.ConnectionStatus.CONNECTING,
    )
    mock_client = MagicMock()
    mock_client_cls.return_value = mock_client
    mock_client.fetch_remote_instance.return_value = None

    url = reverse("integrations-whatsapp-status")
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(user).access_token}")
    response = api_client.get(url)

    assert response.status_code == 200
    assert response.json()["has_instance"] is True
    assert response.json()["needs_reconnect"] is True


@pytest.mark.django_db
@patch("apps.integrations.services.instance_dashboard.EvolutionClient")
@patch("apps.integrations.services.provisioning.EvolutionClient")
def test_whatsapp_provision_after_remote_deleted(
    mock_prov_cls,
    mock_dash_cls,
    api_client,
):
    tenant = TenantFactory(slug="ghost-co")
    user = UserFactory(tenant=tenant, email="wa-ghost@example.com")
    WhatsappInstanceFactory(
        tenant=tenant,
        is_active=True,
        instance_name="mc-ghost-co",
        connection_status=WhatsappInstance.ConnectionStatus.CONNECTING,
    )
    mock_client = MagicMock()
    mock_prov_cls.return_value = mock_client
    mock_dash_cls.return_value = mock_client
    mock_client.check_evolution_health.return_value = "ok"
    mock_client.fetch_remote_instance.side_effect = [
        None,
        {"instanceName": "mc-ghost-co"},
    ]
    mock_client.create_instance_safe.return_value = {"ok": True}
    mock_client.connect_instance.return_value = {"ok": True}
    mock_client.fetch_qrcode.return_value = {
        "data": {"Qrcode": f"data:image/png;base64,{'C' * 120}"},
    }

    url = reverse("integrations-whatsapp-provision")
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(user).access_token}")
    response = api_client.post(url, {}, format="json")

    assert response.status_code == 201
    assert response.json()["has_instance"] is True


@pytest.mark.django_db
def test_whatsapp_get_allowed_non_admin(api_client):
    tenant = TenantFactory()
    user = UserFactory(tenant=tenant, email="wa-read@example.com", is_tenant_admin=False)
    url = reverse("integrations-whatsapp")
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(user).access_token}")
    response = api_client.get(url)
    assert response.status_code == 200
    assert response.json()["has_instance"] is False


@pytest.mark.django_db
def test_whatsapp_provision_forbidden_non_admin(api_client):
    tenant = TenantFactory()
    user = UserFactory(tenant=tenant, email="wa-member@example.com", is_tenant_admin=False)
    url = reverse("integrations-whatsapp-provision")
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(user).access_token}")
    response = api_client.post(url, {}, format="json")
    assert response.status_code == 403


@pytest.mark.django_db
def test_whatsapp_tenant_isolation(api_client):
    tenant_a = TenantFactory()
    tenant_b = TenantFactory()
    user_a = UserFactory(tenant=tenant_a, email="wa-a@example.com")
    WhatsappInstanceFactory(
        tenant=tenant_b,
        instance_name="mc-other",
        is_active=True,
    )

    url = reverse("integrations-whatsapp")
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(user_a).access_token}")
    response = api_client.get(url)
    assert response.status_code == 200
    assert response.json()["has_instance"] is False


@pytest.mark.django_db
def test_evolution_webhook_invalid_secret(api_client):
    inst = WhatsappInstanceFactory(webhook_secret="super-secret")
    url = reverse("webhook-evolution")
    response = api_client.post(
        f"{url}?secret=wrong",
        {
            "event": "CONNECTION",
            "instance": inst.instance_name,
            "data": {"state": "open"},
        },
        format="json",
    )
    assert response.status_code == 403


@pytest.mark.django_db
@patch("django.conf.settings.DEBUG", False)
def test_evolution_webhook_valid_secret(api_client, settings):
    settings.DEBUG = False
    inst = WhatsappInstanceFactory(
        webhook_secret="super-secret",
        connection_status=WhatsappInstance.ConnectionStatus.CONNECTING,
    )
    url = reverse("webhook-evolution")
    response = api_client.post(
        f"{url}?secret=super-secret",
        {
            "event": "CONNECTION",
            "instance": inst.instance_name,
            "data": {"state": "open"},
        },
        format="json",
    )
    assert response.status_code == 200
    inst.refresh_from_db()
    assert inst.connection_status == WhatsappInstance.ConnectionStatus.OPEN
    assert inst.last_webhook_at is not None


@pytest.mark.django_db
@patch("django.conf.settings.DEBUG", False)
def test_evolution_webhook_resolve_by_secret_without_instance_key(api_client, settings):
    settings.DEBUG = False
    inst = WhatsappInstanceFactory(
        webhook_secret="only-secret-match",
        connection_status=WhatsappInstance.ConnectionStatus.CONNECTING,
    )
    url = reverse("webhook-evolution")
    response = api_client.post(
        f"{url}?secret=only-secret-match",
        {"event": "CONNECTION", "data": {"state": "open"}},
        format="json",
    )
    assert response.status_code == 200
    inst.refresh_from_db()
    assert inst.connection_status == WhatsappInstance.ConnectionStatus.OPEN


@pytest.mark.django_db
@patch("django.conf.settings.DEBUG", False)
def test_evolution_webhook_inactive_instance_by_secret(api_client, settings):
    settings.DEBUG = False
    inst = WhatsappInstanceFactory(
        webhook_secret="inactive-secret",
        is_active=False,
        connection_status=WhatsappInstance.ConnectionStatus.CONNECTING,
    )
    url = reverse("webhook-evolution")
    response = api_client.post(
        f"{url}?secret=inactive-secret",
        {"event": "CONNECTION", "instance": inst.instance_name, "data": {"state": "open"}},
        format="json",
    )
    assert response.status_code == 200
    inst.refresh_from_db()
    assert inst.connection_status == WhatsappInstance.ConnectionStatus.OPEN


@pytest.mark.django_db
@patch("django.conf.settings.DEBUG", False)
@patch("apps.sales.services.cart_flow.route_idle_message", return_value=True)
def test_evolution_webhook_allowed_by_apikey_header(
    mock_route,
    api_client,
    settings,
):
    settings.DEBUG = False
    tenant = TenantFactory()
    resident = ResidentFactory(tenant=tenant, phone_number="5511999001122")
    inst = WhatsappInstanceFactory(
        tenant=tenant,
        webhook_secret="only-in-url",
        api_key="instance-api-key-xyz",
        is_active=True,
    )
    url = reverse("webhook-evolution")
    response = api_client.post(
        url,
        {
            "event": "MESSAGE",
            "instance": inst.instance_name,
            "data": {
                "key": {
                    "remoteJid": f"{resident.phone_number}@s.whatsapp.net",
                    "id": "msg-apikey-1",
                    "fromMe": False,
                },
                "message": {"conversation": "oi"},
            },
        },
        format="json",
        HTTP_APIKEY="instance-api-key-xyz",
    )
    assert response.status_code == 200
    mock_route.assert_called_once()


@pytest.mark.django_db
def test_evolution_webhook_unknown_instance(api_client):
    url = reverse("webhook-evolution")
    response = api_client.post(
        f"{url}?secret=any",
        {"event": "CONNECTION", "instance": "nonexistent", "data": {"state": "open"}},
        format="json",
    )
    assert response.status_code == 404


@pytest.mark.django_db
@patch("apps.integrations.services.provisioning.EvolutionClient")
def test_provision_service_unit(mock_client_cls):
    tenant = TenantFactory(slug="svc-test")
    mock_client = MagicMock()
    mock_client_cls.return_value = mock_client
    mock_client.create_instance_safe.return_value = {}
    mock_client.connect_instance.return_value = {}
    mock_client.connection_state.return_value = {"loggedIn": True, "connected": True}
    mock_client.fetch_remote_instance.return_value = {"instanceName": "mc-svc-test"}

    result = provision_whatsapp_instance(tenant, client=mock_client)
    assert result["instance"].instance_name == "mc-svc-test"
    mock_client.create_instance_safe.assert_called_once()
    mock_client.connect_instance.assert_called_once()

    with pytest.raises(WhatsappAlreadyProvisionedError):
        provision_whatsapp_instance(tenant, client=mock_client)


@pytest.mark.django_db
@patch("apps.integrations.services.profile_sync.EvolutionClient")
def test_sync_profile_avatar_from_evolution(mock_client_cls):
    from apps.integrations.services.profile_sync import sync_profile_avatar_from_evolution

    inst = WhatsappInstanceFactory(
        connection_status=WhatsappInstance.ConnectionStatus.OPEN,
        phone_number="5511987654321",
        api_key="test-api-key",
    )
    mock_client = MagicMock()
    mock_client_cls.return_value = mock_client
    mock_client.fetch_remote_instance.return_value = {
        "jid": "5511987654321:1@s.whatsapp.net",
    }
    mock_client.fetch_user_avatar.return_value = {
        "data": {"url": "https://evo.example/avatar/me.jpg"},
    }
    mock_client.extract_avatar_image.return_value = "https://evo.example/avatar/me.jpg"

    assert sync_profile_avatar_from_evolution(inst) is True
    inst.refresh_from_db()
    assert inst.profile_picture_url == "https://evo.example/avatar/me.jpg"
    mock_client.fetch_remote_instance.assert_called()
    mock_client.fetch_user_avatar.assert_called()
    call_kwargs = mock_client.fetch_user_avatar.call_args.kwargs
    assert call_kwargs["instance_api_key"] == "test-api-key"
    assert call_kwargs["number"].endswith("@s.whatsapp.net")


@pytest.mark.django_db
@patch("apps.integrations.services.instance_dashboard.EvolutionClient")
@patch("apps.integrations.services.provisioning.EvolutionClient")
def test_whatsapp_dashboard_webhook_status(mock_prov_cls, mock_dash_cls, api_client):
    tenant = TenantFactory()
    user = UserFactory(tenant=tenant, email="wa-dash@example.com")
    mock_client = _mock_evolution_client()
    mock_client.connection_state.return_value = {"data": {"state": "open"}}
    mock_prov_cls.return_value = mock_client
    mock_dash_cls.return_value = mock_client
    mock_client.fetch_remote_instance.return_value = None
    mock_client.extract_avatar_image.return_value = ""

    inst = WhatsappInstanceFactory(
        tenant=tenant,
        is_active=True,
        connection_status=WhatsappInstance.ConnectionStatus.OPEN,
        last_webhook_at=timezone.now(),
    )
    url = reverse("integrations-whatsapp")
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(user).access_token}")
    response = api_client.get(url)
    assert response.status_code == 200
    data = response.json()
    assert data["has_instance"] is True
    assert data["webhook_status"] == "ok"
    assert data["evolution_api_status"] == "ok"
    assert inst.instance_name == data["instance_name"]


@pytest.mark.django_db
@patch("apps.integrations.services.instance_dashboard.EvolutionClient")
@patch("apps.integrations.services.provisioning.EvolutionClient")
def test_whatsapp_dashboard_webhook_stale(mock_prov_cls, mock_dash_cls, api_client):
    tenant = TenantFactory()
    user = UserFactory(tenant=tenant, email="wa-stale@example.com")
    mock_client = _mock_evolution_client()
    mock_client.connection_state.return_value = {"data": {"state": "open"}}
    mock_prov_cls.return_value = mock_client
    mock_dash_cls.return_value = mock_client
    mock_client.fetch_remote_instance.return_value = None
    mock_client.extract_avatar_image.return_value = ""

    WhatsappInstanceFactory(
        tenant=tenant,
        is_active=True,
        connection_status=WhatsappInstance.ConnectionStatus.OPEN,
        last_webhook_at=timezone.now() - timedelta(minutes=15),
    )
    url = reverse("integrations-whatsapp")
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(user).access_token}")
    response = api_client.get(url)
    assert response.json()["webhook_status"] == "error"


@pytest.mark.django_db
@patch("apps.integrations.services.restart.EvolutionClient")
def test_whatsapp_restart(mock_client_cls, api_client):
    """CLOSE → recria instância no Evolution (connect sozinho não gera QR)."""
    tenant = TenantFactory()
    user = UserFactory(tenant=tenant, email="wa-restart@example.com")
    inst = WhatsappInstanceFactory(
        tenant=tenant,
        is_active=True,
        connection_status=WhatsappInstance.ConnectionStatus.CLOSE,
        webhook_url="http://localhost/api/integrations/webhooks/evolution/?secret=test",
        instance_name="mc-restart-test",
        instance_id="old-id",
        api_key="old-token",
    )
    mock_client = MagicMock()
    mock_client_cls.return_value = mock_client

    url = reverse("integrations-whatsapp-restart")
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(user).access_token}")
    response = api_client.post(url, {}, format="json")
    assert response.status_code == 200
    mock_client.reconnect_instance.assert_not_called()
    mock_client.create_instance_safe.assert_called_once()
    mock_client.connect_instance.assert_called_once()
    data = response.json()
    assert data["has_instance"] is True
    assert data["connection_status"] == "connecting"
    inst.refresh_from_db()
    assert inst.connection_status == WhatsappInstance.ConnectionStatus.CONNECTING
    assert inst.api_key != "old-token"


def _http_error(code: int, body: str) -> urllib.error.HTTPError:
    exc = urllib.error.HTTPError(
        "http://localhost:8080/instance/status",
        code,
        "Bad Request" if code == 400 else "Error",
        {},
        None,
    )
    exc._body_preview = body.encode()
    return exc


@pytest.mark.django_db
@patch("apps.integrations.services.provisioning.EvolutionClient")
def test_sync_connection_status_preserves_connecting_during_qr(mock_client_cls):
    inst = WhatsappInstanceFactory(
        is_active=True,
        connection_status=WhatsappInstance.ConnectionStatus.CONNECTING,
    )
    mock_client = MagicMock()
    mock_client_cls.return_value = mock_client
    mock_client.connection_state.side_effect = _http_error(
        400,
        '{"error":"client disconnected"}',
    )

    status = sync_connection_status(inst, client=mock_client)

    assert status == WhatsappInstance.ConnectionStatus.CONNECTING
    inst.refresh_from_db()
    assert inst.connection_status == WhatsappInstance.ConnectionStatus.CONNECTING


@pytest.mark.django_db
@patch("apps.integrations.services.provisioning.EvolutionClient")
def test_sync_connection_status_client_disconnected_keeps_instance_active(mock_client_cls):
    inst = WhatsappInstanceFactory(
        is_active=True,
        connection_status=WhatsappInstance.ConnectionStatus.OPEN,
        phone_number="5511999887766",
    )
    mock_client = MagicMock()
    mock_client_cls.return_value = mock_client
    mock_client.connection_state.side_effect = _http_error(
        400,
        '{"error":"client disconnected"}',
    )

    status = sync_connection_status(inst, client=mock_client)

    assert status == WhatsappInstance.ConnectionStatus.CLOSE
    inst.refresh_from_db()
    assert inst.is_active is True
    assert inst.disconnect_reason


@pytest.mark.django_db
@patch("apps.integrations.services.instance_dashboard.EvolutionClient")
@patch("apps.integrations.services.provisioning.EvolutionClient")
def test_whatsapp_dashboard_needs_reconnect_after_session_drop(
    mock_prov_cls,
    mock_dash_cls,
    api_client,
):
    tenant = TenantFactory()
    user = UserFactory(tenant=tenant, email="wa-reconnect-dash@example.com")
    WhatsappInstanceFactory(
        tenant=tenant,
        is_active=True,
        connection_status=WhatsappInstance.ConnectionStatus.CLOSE,
        phone_number="5511999887766",
        profile_name="Mercado Central",
        disconnect_reason="WhatsApp desconectado no celular.",
    )
    mock_client = _mock_evolution_client()
    mock_prov_cls.return_value = mock_client
    mock_dash_cls.return_value = mock_client
    mock_client.connection_state.return_value = {"data": {"state": "close"}}

    url = reverse("integrations-whatsapp")
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(user).access_token}")
    response = api_client.get(url)

    assert response.status_code == 200
    data = response.json()
    assert data["has_instance"] is True
    assert data["needs_reconnect"] is True
    assert data["was_connected"] is True
    assert data["connected"] is False
    assert data["phone_number"] == "5511999887766"


@pytest.mark.django_db
@patch("apps.integrations.services.provisioning.EvolutionClient")
def test_reconcile_close_with_phone_does_not_deactivate(mock_client_cls):
    from apps.integrations.services.provisioning import reconcile_whatsapp_with_evolution

    inst = WhatsappInstanceFactory(
        is_active=True,
        connection_status=WhatsappInstance.ConnectionStatus.CLOSE,
        phone_number="5511999887766",
    )
    mock_client = MagicMock()
    mock_client_cls.return_value = mock_client
    mock_client.connection_state.return_value = {"data": {"state": "close"}}
    mock_client.fetch_remote_instance.return_value = None

    result = reconcile_whatsapp_with_evolution(inst, client=mock_client)

    assert result is not None
    inst.refresh_from_db()
    assert inst.is_active is True


@pytest.mark.django_db
def test_mark_whatsapp_session_disconnected():
    inst = WhatsappInstanceFactory(
        is_active=True,
        connection_status=WhatsappInstance.ConnectionStatus.OPEN,
    )
    mark_whatsapp_session_disconnected(inst, reason="Sessão expirou.")
    inst.refresh_from_db()
    assert inst.is_active is True
    assert inst.connection_status == WhatsappInstance.ConnectionStatus.CLOSE
    assert inst.disconnect_reason == "Sessão expirou."

import json
from io import BytesIO
from unittest.mock import MagicMock, patch

import pytest
import urllib.error

from apps.integrations.services.evolution_client import EvolutionClient


def test_delete_instance_uses_resolved_uuid():
    client = EvolutionClient(base_url="http://evo.test", global_api_key="global")
    remote_uuid = "421a4121-a3d9-40cc-a8db-c3a1df353126"

    with patch.object(
        client,
        "resolve_remote_instance_id",
        return_value=remote_uuid,
    ):
        with patch.object(client, "_request", return_value={"ok": True}) as mock_req:
            result = client.delete_instance(
                instance_name="mc-acme",
                instance_id="stale-id",
            )
    assert result == {"ok": True}
    mock_req.assert_called_once()
    assert remote_uuid in mock_req.call_args[0][1]


def test_delete_instance_returns_empty_when_not_resolved():
    client = EvolutionClient(base_url="http://evo.test", global_api_key="global")
    with patch.object(client, "resolve_remote_instance_id", return_value=""):
        with patch.object(client, "_request") as mock_req:
            result = client.delete_instance(instance_name="mc-missing")
    assert result == {}
    mock_req.assert_not_called()


def test_create_instance_safe_retries_after_already_exists():
    client = EvolutionClient(base_url="http://evo.test", global_api_key="global")
    exists_err = urllib.error.HTTPError(
        url="http://evo.test/instance/create",
        code=500,
        msg="err",
        hdrs={},
        fp=BytesIO(b'{"error":"instance already exists"}'),
    )
    exists_err._body_preview = b'{"error":"instance already exists"}'  # type: ignore[attr-defined]

    with patch.object(
        client,
        "create_instance",
        side_effect=[exists_err, {"ok": True}],
    ) as mock_create:
        with patch.object(client, "delete_instance", return_value={}) as mock_delete:
            payload = client.create_instance_safe(
                name="mc-acme",
                instance_id="421a4121-a3d9-40cc-a8db-c3a1df353126",
                token="tok",
            )
    assert payload == {"ok": True}
    mock_delete.assert_called_once_with(
        instance_name="mc-acme",
        instance_id="421a4121-a3d9-40cc-a8db-c3a1df353126",
    )
    assert mock_create.call_count == 2


def test_resolve_remote_instance_id_from_fetch():
    client = EvolutionClient(base_url="http://evo.test", global_api_key="global")
    with patch.object(
        client,
        "fetch_instances",
        return_value=[
            {
                "instanceName": "mc-viva-software",
                "instanceId": "af6c5b7c-ee27-4f94-9ea8-192393746ddd",
            }
        ],
    ):
        rid = client.resolve_remote_instance_id(instance_name="mc-viva-software")
    assert rid == "af6c5b7c-ee27-4f94-9ea8-192393746ddd"


def test_parse_fetch_instances_payload_list():
    from apps.integrations.services.evolution_client import _parse_fetch_instances_payload

    rows = _parse_fetch_instances_payload(
        [{"instance": {"instanceName": "a", "instanceId": "421a4121-a3d9-40cc-a8db-c3a1df353126"}}]
    )
    assert rows[0]["instanceName"] == "a"


def test_parse_fetch_instances_evoapicloud_all():
    from apps.integrations.services.evolution_client import _parse_fetch_instances_payload

    rows = _parse_fetch_instances_payload(
        {
            "data": [
                {
                    "id": "5db5a7e4-1581-4963-9ee6-2e1903f55443",
                    "name": "mc-viva-software",
                }
            ]
        }
    )
    assert rows[0]["instanceId"] == "5db5a7e4-1581-4963-9ee6-2e1903f55443"
    assert rows[0]["instanceName"] == "mc-viva-software"


def test_check_evolution_health_ok():
    client = EvolutionClient(base_url="http://evo.test", global_api_key="global")
    with patch.object(client, "_request", return_value={"data": []}):
        assert client.check_evolution_health() == "ok"


def test_check_evolution_health_error():
    client = EvolutionClient(base_url="http://evo.test", global_api_key="global")
    with patch.object(client, "_request", side_effect=RuntimeError("down")):
        assert client.check_evolution_health() == "error"


def test_restart_instance_uses_evolution_go_reconnect():
    client = EvolutionClient(base_url="http://evo.test", global_api_key="global")
    with patch.object(client, "reconnect_instance", return_value={"ok": True}) as mock_reconnect:
        result = client.restart_instance(
            instance_api_key="tok",
            webhook_url="https://app.example/webhook",
        )
    assert result == {"ok": True}
    mock_reconnect.assert_called_once_with(
        instance_api_key="tok",
        webhook_url="https://app.example/webhook",
        events=None,
        phone="",
        reset_session=False,
    )


def test_reconnect_instance_fast_path_skips_qr_wait():
    client = EvolutionClient(base_url="http://evo.test", global_api_key="global")
    with patch.object(
        client,
        "_connect_for_qr",
        return_value={"message": "success"},
    ) as mock_connect:
        with patch.object(client, "_fetch_qrcode_after_connect") as mock_qr:
            result = client.reconnect_instance(
                instance_api_key="tok",
                webhook_url="https://app.example/webhook",
            )
    assert result["qr_pending"] is True
    assert result["connect"] == {"message": "success"}
    mock_connect.assert_called_once()
    mock_qr.assert_not_called()


def test_reconnect_instance_calls_connect_and_qr_when_wait_enabled():
    client = EvolutionClient(base_url="http://evo.test", global_api_key="global")
    with patch.object(
        client,
        "_connect_for_qr",
        return_value={"message": "success"},
    ) as mock_connect:
        with patch.object(
            client,
            "_fetch_qrcode_after_connect",
            return_value={"data": {"Qrcode": f"data:image/png;base64,{'A' * 120}"}},
        ) as mock_qr:
            result = client.reconnect_instance(
                instance_api_key="tok",
                webhook_url="https://app.example/webhook",
                wait_for_qr=True,
            )
    assert result["connect"] == {"message": "success"}
    mock_connect.assert_called_once()
    mock_qr.assert_called_once()


def test_logout_instance_treats_client_disconnected_as_success():
    client = EvolutionClient(base_url="http://evo.test", global_api_key="global")
    exc = urllib.error.HTTPError(
        "http://evo.test/instance/logout",
        400,
        "Bad Request",
        {},
        None,
    )
    exc._body_preview = b'{"error":"client disconnected"}'
    with patch.object(client, "_request", side_effect=exc):
        assert client.logout_instance(instance_api_key="tok") == {}


def test_connect_for_qr_uses_immediate_without_phone():
    client = EvolutionClient(base_url="http://evo.test", global_api_key="global")
    with patch.object(
        client,
        "connect_instance",
        return_value={"message": "success"},
    ) as mock_connect:
        client._connect_for_qr(
            instance_api_key="tok",
            webhook_url="https://app.example/webhook",
            events=["MESSAGE", "QRCODE"],
        )
    mock_connect.assert_called_once_with(
        instance_api_key="tok",
        webhook_url="https://app.example/webhook",
        events=["MESSAGE", "QRCODE"],
        phone="",
        immediate=True,
    )


def _qr_not_ready_error() -> urllib.error.HTTPError:
    exc = urllib.error.HTTPError(
        "http://evo.test/instance/qr",
        400,
        "Bad Request",
        {},
        None,
    )
    exc._body_preview = b'{"error":"no QR code available. Please wait a moment and try again"}'
    return exc


def test_fetch_qrcode_retries_when_not_ready():
    client = EvolutionClient(base_url="http://evo.test", global_api_key="global")
    ok_payload = {"data": {"Qrcode": f"data:image/png;base64,{'Z' * 120}"}}
    with patch.object(client, "_request", side_effect=[_qr_not_ready_error(), ok_payload]) as mock_req:
        with patch("apps.integrations.services.evolution_client.time.sleep") as mock_sleep:
            result = client.fetch_qrcode(instance_api_key="tok", retries=2, retry_delay=0.01)
    assert result == ok_payload
    assert mock_req.call_count == 2
    mock_sleep.assert_called_once_with(0.01)


def test_extract_avatar_image_url():
    client = EvolutionClient(base_url="http://evo.test", global_api_key="global")
    payload = {"data": {"url": "https://cdn.example/avatar.jpg"}}
    assert client.extract_avatar_image(payload) == "https://cdn.example/avatar.jpg"


def test_extract_avatar_image_base64():
    client = EvolutionClient(base_url="http://evo.test", global_api_key="global")
    raw = "A" * 100
    payload = {"base64": raw}
    out = client.extract_avatar_image(payload)
    assert out.startswith("data:image/jpeg;base64,")


def test_normalize_avatar_target_digits():
    assert (
        EvolutionClient.normalize_avatar_target("5511999998888")
        == "5511999998888@s.whatsapp.net"
    )


def test_normalize_avatar_target_jid_with_device():
    assert (
        EvolutionClient.normalize_avatar_target("5511999998888:5@s.whatsapp.net")
        == "5511999998888@s.whatsapp.net"
    )


def test_fetch_user_avatar_request():
    client = EvolutionClient(base_url="http://evo.test", global_api_key="global")
    with patch.object(client, "_request", return_value={"url": "https://x/a.jpg"}) as mock_req:
        result = client.fetch_user_avatar(
            number="+55 (11) 99999-8888",
            instance_api_key="inst-key",
        )
    assert result["url"] == "https://x/a.jpg"
    mock_req.assert_called_once()
    assert mock_req.call_args[1]["body"] == {
        "number": "5511999998888@s.whatsapp.net",
        "preview": True,
    }


def test_extract_avatar_image_data_url():
    client = EvolutionClient(base_url="http://evo.test", global_api_key="global")
    payload = {"data": {"url": "https://pps.whatsapp.net/avatar.jpg"}}
    assert client.extract_avatar_image(payload) == "https://pps.whatsapp.net/avatar.jpg"


def test_fetch_remote_instance():
    client = EvolutionClient(base_url="http://evo.test", global_api_key="global")
    row = {"instanceName": "mc-acme", "connected": True}
    with patch.object(client, "fetch_instances", return_value=[row]):
        assert client.fetch_remote_instance(instance_name="mc-acme") == row


def test_fetch_instances_does_not_fallback_on_503():
    client = EvolutionClient(base_url="http://evo.test", global_api_key="global")
    err = urllib.error.HTTPError(
        "http://evo.test/instance/all",
        503,
        "Service Unavailable",
        {},
        None,
    )
    with patch.object(client, "_request", side_effect=err):
        with pytest.raises(urllib.error.HTTPError) as raised:
            client.fetch_instances()
    assert raised.value.code == 503


def test_build_webhook_url_appends_path_when_origin_only():
    url = EvolutionClient.build_webhook_url(
        "https://staging-api.example.com",
        "abcSecretToken",
    )
    assert url == (
        "https://staging-api.example.com/api/integrations/webhooks/evolution/"
        "?secret=abcSecretToken"
    )


def test_build_webhook_url_preserves_full_path():
    base = "https://api.example.com/api/integrations/webhooks/evolution/"
    url = EvolutionClient.build_webhook_url(base, "tok")
    assert url == f"{base}?secret=tok"


def test_build_webhook_url_repairs_origin_with_existing_secret_query():
    url = EvolutionClient.build_webhook_url(
        "https://staging-api.example.com?secret=already",
        "ignored",
    )
    assert url == (
        "https://staging-api.example.com/api/integrations/webhooks/evolution/"
        "?secret=already"
    )

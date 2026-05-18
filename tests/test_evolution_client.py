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


def test_restart_instance_put():
    client = EvolutionClient(base_url="http://evo.test", global_api_key="global")
    with patch.object(client, "_request", return_value={"ok": True}) as mock_req:
        result = client.restart_instance(instance_name="mc-acme", instance_api_key="tok")
    assert result == {"ok": True}
    assert "/instance/restart/mc-acme" in mock_req.call_args[0][1]
    assert mock_req.call_args[1]["apikey"] == "tok"


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

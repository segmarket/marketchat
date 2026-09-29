"""Normalização do QRCODE Evolution-Go para data URI (sem GET /instance/qr)."""

from __future__ import annotations

import base64

import pytest
from django.core.cache import cache
from django.urls import reverse
from rest_framework_simplejwt.tokens import RefreshToken
from unittest.mock import MagicMock, patch

from apps.integrations.models import WhatsappInstance
from apps.integrations.services.evolution_qr import (
    DATA_URI_PREFIX,
    normalize_evolution_qr,
)
from apps.integrations.services.evolution_session import get_cached_pairing_qr
from apps.integrations.services.webhook_handlers import handle_evolution_webhook
from apps.integrations.services.webhook_parser import EvolutionWebhookEvent
from tests.factories import TenantFactory, UserFactory, WhatsappInstanceFactory

TINY_PNG_B64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
)
WA_ME = (
    "https://wa.me/settings/linked_devices#code=ABC123DEF456GHI789JKL012MNO345PQR"
)


@pytest.fixture(autouse=True)
def _clear_cache():
    cache.clear()
    yield
    cache.clear()


def test_normalize_png_base64_gets_data_uri_prefix():
    out = normalize_evolution_qr({"qrcode": TINY_PNG_B64, "code": "2@abc,def,ghi,jkl"})
    assert out.startswith(DATA_URI_PREFIX)
    assert out == f"{DATA_URI_PREFIX}{TINY_PNG_B64}"
    decoded = base64.b64decode(out.split(",", 1)[1])
    assert decoded.startswith(b"\x89PNG")


def test_normalize_prefers_qrcode_png_over_code_text():
    payload = {
        "event": "QRCODE",
        "data": {
            "code": "2@THIS-IS-PAIRING-TEXT-NOT-AN-IMAGE,aaaa,bbbb,cccc",
            "qrcode": TINY_PNG_B64,
        },
    }
    out = normalize_evolution_qr(payload)
    raw = base64.b64decode(out.split(",", 1)[1])
    assert raw.startswith(b"\x89PNG")
    assert b"THIS-IS-PAIRING" not in raw


def test_normalize_wa_me_generates_png_and_never_uses_url_as_src():
    out = normalize_evolution_qr({"qrcode": WA_ME, "code": "2@abc,def,ghi,jklmnop"})
    assert out.startswith(DATA_URI_PREFIX)
    assert "wa.me" not in out
    decoded = base64.b64decode(out.split(",", 1)[1])
    assert decoded.startswith(b"\x89PNG")


def test_normalize_code_only_pairing_text_generates_png():
    out = normalize_evolution_qr({"code": "2@ABC123DEF456,GHI789JKL012,MNO345,PQR678"})
    assert out.startswith(DATA_URI_PREFIX)
    decoded = base64.b64decode(out.split(",", 1)[1])
    assert decoded.startswith(b"\x89PNG")


def test_normalize_empty_is_invalid():
    assert normalize_evolution_qr({"qrcode": "", "code": ""}) == ""
    assert normalize_evolution_qr({}) == ""


@pytest.mark.django_db
@patch("apps.integrations.services.webhook_handlers.sync_profile_avatar_from_evolution")
def test_webhook_wa_me_caches_png_data_uri(mock_avatar):
    del mock_avatar
    inst = WhatsappInstanceFactory(
        is_active=True,
        connection_status=WhatsappInstance.ConnectionStatus.CONNECTING,
    )
    handle_evolution_webhook(
        EvolutionWebhookEvent(
            event_type="QRCODE",
            instance_key=inst.instance_name,
            connection_state="",
            remote_jid="",
            message_id="",
            from_me=False,
            raw_message={"qrcode": WA_ME, "code": "2@abc,def,ghi,jklmnop"},
        ),
        inst,
    )
    cached = get_cached_pairing_qr(inst)
    assert cached.startswith("data:image/png;base64,")
    assert "wa.me" not in cached
    assert "https://" not in cached


@pytest.mark.django_db
@patch("apps.integrations.services.webhook_handlers.sync_profile_avatar_from_evolution")
def test_webhook_empty_qr_does_not_cache(mock_avatar):
    del mock_avatar
    inst = WhatsappInstanceFactory(
        is_active=True,
        connection_status=WhatsappInstance.ConnectionStatus.CONNECTING,
    )
    handle_evolution_webhook(
        EvolutionWebhookEvent(
            event_type="QRCODE",
            instance_key=inst.instance_name,
            connection_state="",
            remote_jid="",
            message_id="",
            from_me=False,
            raw_message={"qrcode": "", "code": ""},
        ),
        inst,
    )
    assert get_cached_pairing_qr(inst) == ""
    inst.refresh_from_db()
    assert inst.connection_status == WhatsappInstance.ConnectionStatus.CONNECTING


@pytest.mark.django_db
@patch("apps.integrations.services.instance_dashboard.EvolutionClient")
@patch("apps.integrations.services.provisioning.EvolutionClient")
@patch("apps.integrations.services.webhook_handlers.sync_profile_avatar_from_evolution")
def test_status_returns_normalized_qr_image(
    mock_avatar,
    mock_prov_cls,
    mock_dash_cls,
    api_client,
):
    del mock_avatar
    tenant = TenantFactory()
    user = UserFactory(tenant=tenant, email="wa-qr-img@example.com")
    inst = WhatsappInstanceFactory(
        tenant=tenant,
        is_active=True,
        connection_status=WhatsappInstance.ConnectionStatus.CONNECTING,
    )
    mock_client = MagicMock()
    mock_prov_cls.return_value = mock_client
    mock_dash_cls.return_value = mock_client
    mock_client.connection_state.return_value = {"data": {"state": "connecting"}}
    mock_client.check_evolution_health.return_value = "ok"
    mock_client.fetch_qrcode.assert_not_called()

    handle_evolution_webhook(
        EvolutionWebhookEvent(
            event_type="QRCODE",
            instance_key=inst.instance_name,
            connection_state="",
            remote_jid="",
            message_id="",
            from_me=False,
            raw_message={"qrcode": TINY_PNG_B64, "code": "2@abc,def,ghi,jkl"},
        ),
        inst,
    )
    api_client.credentials(
        HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(user).access_token}"
    )
    response = api_client.get(reverse("integrations-whatsapp-status"))
    assert response.status_code == 200
    data = response.json()
    assert data["qr_image"].startswith("data:image/png;base64,")
    assert data["qrcode_image"].startswith("data:image/png;base64,")
    mock_client.fetch_qrcode.assert_not_called()
    mock_client.connect_instance.assert_not_called()

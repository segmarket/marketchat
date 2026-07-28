from decimal import Decimal
from unittest import mock

import pytest
from django.core.cache import cache
from django.urls import reverse
from rest_framework_simplejwt.tokens import RefreshToken

from tests.factories import TenantFactory, UserFactory
from tests.test_asaas_cart_webhook import BILLING_WEBHOOK_URL, _payment_payload


def _auth_client(api_client, user):
    api_client.credentials(
        HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(user).access_token}"
    )
    return api_client


@pytest.fixture(autouse=True)
def clear_throttle_cache():
    cache.clear()
    yield
    cache.clear()


@pytest.mark.django_db
def test_login_throttle_blocks_after_five_attempts(settings, api_client):
    settings.TRUST_X_FORWARDED_FOR = True
    url = reverse("token_obtain_pair")
    payload = {"email": "unknown@example.com", "password": "wrong-password"}
    headers = {"HTTP_X_FORWARDED_FOR": "203.0.113.50"}

    for _ in range(5):
        response = api_client.post(url, payload, format="json", **headers)
        assert response.status_code in (400, 401)

    response = api_client.post(url, payload, format="json", **headers)
    assert response.status_code == 429


@pytest.mark.django_db
@mock.patch("apps.financial.services.wallet.process_asaas_pix_transfer")
def test_withdraw_throttle_blocks_after_five_requests(mock_transfer, settings, api_client):
    settings.TRUST_X_FORWARDED_FOR = True
    mock_transfer.side_effect = [
        {"id": f"tra_throttle_{i}", "status": "DONE"} for i in range(5)
    ]

    tenant = TenantFactory()
    user = UserFactory(tenant=tenant, is_tenant_admin=True)
    from apps.financial.models import Wallet

    Wallet.objects.create(
        tenant=tenant,
        balance_available=Decimal("1000.00"),
        default_pix_key="mercado@example.com",
        default_pix_key_type="EMAIL",
    )

    url = reverse("financial-withdraw")
    _auth_client(api_client, user)

    for _ in range(5):
        response = api_client.post(url, {"amount": "1.00"}, format="json")
        assert response.status_code == 201

    response = api_client.post(url, {"amount": "1.00"}, format="json")
    assert response.status_code == 429


@pytest.mark.django_db
def test_webhook_not_throttled(settings, api_client):
    settings.ASAAS_WEBHOOK_VERIFY = False

    for _ in range(12):
        response = api_client.post(
            BILLING_WEBHOOK_URL,
            _payment_payload(event="PAYMENT_RECEIVED", payment_id="pay_throttle"),
            format="json",
        )
        assert response.status_code == 200


@pytest.mark.django_db
def test_evolution_webhook_not_throttled(settings, api_client):
    """Webhook Evolution não pode usar o throttle anon (10/min) — perde mensagens."""
    settings.TRUST_X_FORWARDED_FOR = True
    from apps.integrations.models import WhatsappInstance
    from tests.factories import WhatsappInstanceFactory

    inst = WhatsappInstanceFactory(
        webhook_secret="evo-throttle-secret",
        connection_status=WhatsappInstance.ConnectionStatus.OPEN,
    )
    url = reverse("webhook-evolution")
    headers = {"HTTP_X_FORWARDED_FOR": "198.51.100.77"}
    payload = {
        "event": "CONNECTION",
        "instance": inst.instance_name,
        "data": {"state": "open"},
    }

    for i in range(15):
        response = api_client.post(
            f"{url}?secret=evo-throttle-secret",
            payload,
            format="json",
            **headers,
        )
        assert response.status_code == 200, f"request {i + 1} got {response.status_code}"

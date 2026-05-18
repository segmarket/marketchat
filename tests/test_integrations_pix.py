import json
from unittest import mock

import pytest
from django.urls import reverse
from rest_framework_simplejwt.tokens import RefreshToken

from apps.billing.models import AsaasSubaccount
from tests.factories import MarketFactory, TenantFactory, UserFactory

VALID_MARKET_ADDRESS = json.dumps(
    {
        "cep": "13000000",
        "street": "Av. Brasil",
        "number": "100",
        "complement": "",
        "neighborhood": "Centro",
        "city": "Campinas",
        "state": "SP",
    }
)

PIX_PAYLOAD = {
    "name": "Empresa Pix LTDA",
    "email": "pix@example.com",
    "cpf_cnpj": "12345678901",
    "pix_key_type": "CPF",
    "pix_key": "123.456.789-01",
}


def _auth(client, user):
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(user).access_token}")


def _market_with_address(tenant, phone="11999998888"):
    tenant.phone = phone
    tenant.save(update_fields=["phone", "updated_at"])
    return MarketFactory(tenant=tenant, address=VALID_MARKET_ADDRESS)


@pytest.mark.django_db
def test_pix_put_creates_subaccount_success(api_client):
    tenant = TenantFactory(cpf_cnpj="12345678901")
    user = UserFactory(tenant=tenant, email="admin-pix@example.com")
    _market_with_address(tenant)
    _auth(api_client, user)

    with mock.patch("apps.billing.services.asaas_subaccount.AsaasClient") as mock_cls:
        mock_cls.return_value.create_subaccount.return_value = {
            "walletId": "wal_test_abc123",
        }
        response = api_client.put(reverse("integrations-pix"), PIX_PAYLOAD, format="json")

    assert response.status_code == 200
    data = response.json()
    assert data["asaas_wallet_id"] == "wal_test_abc123"
    assert data["has_wallet"] is True
    assert data["account_status"] == "PENDING"

    sub = AsaasSubaccount.objects.get(tenant=tenant)
    assert sub.asaas_wallet_id == "wal_test_abc123"
    mock_cls.return_value.create_subaccount.assert_called_once()


@pytest.mark.django_db
def test_pix_put_asaas_failure_returns_detail(api_client):
    tenant = TenantFactory()
    user = UserFactory(tenant=tenant, email="pix-fail@example.com")
    _market_with_address(tenant)
    _auth(api_client, user)

    from apps.billing.services.asaas_client import AsaasAPIError

    with mock.patch("apps.billing.services.asaas_subaccount.AsaasClient") as mock_cls:
        mock_cls.return_value.create_subaccount.side_effect = AsaasAPIError(
            "Erro",
            status_code=400,
            payload={"errors": [{"description": "CPF inválido"}]},
        )
        response = api_client.put(reverse("integrations-pix"), PIX_PAYLOAD, format="json")

    assert response.status_code == 400
    assert "CPF inválido" in response.json()["detail"]
    assert not AsaasSubaccount.objects.filter(tenant=tenant, asaas_wallet_id__gt="").exists()


@pytest.mark.django_db
def test_pix_put_without_market_returns_400(api_client):
    tenant = TenantFactory()
    user = UserFactory(tenant=tenant, email="pix-nomarket@example.com")
    tenant.phone = "11999998888"
    tenant.save(update_fields=["phone", "updated_at"])
    _auth(api_client, user)

    response = api_client.put(reverse("integrations-pix"), PIX_PAYLOAD, format="json")
    assert response.status_code == 400
    assert "mercado" in response.json()["detail"].lower()


@pytest.mark.django_db
def test_pix_get_tenant_isolation(api_client):
    tenant_a = TenantFactory(name="Tenant A", cpf_cnpj="11144477735")
    tenant_b = TenantFactory(name="Tenant B")
    user_b = UserFactory(tenant=tenant_b, email="pix-b@example.com")
    _market_with_address(tenant_a)

    AsaasSubaccount.objects.create(
        tenant=tenant_a,
        name="Sub A",
        email="a@example.com",
        cpf_cnpj="11144477735",
        pix_key_type=AsaasSubaccount.PixKeyType.CPF,
        pix_key="11144477735",
        asaas_wallet_id="wal_tenant_a_only",
        account_status=AsaasSubaccount.AccountStatus.APPROVED,
    )

    _auth(api_client, user_b)
    response = api_client.get(reverse("integrations-pix"))
    assert response.status_code == 200
    data = response.json()
    assert data["asaas_wallet_id"] == ""
    assert data["has_wallet"] is False
    assert data["prefill"]["name"] == "Tenant B"


@pytest.mark.django_db
def test_pix_put_updates_local_when_wallet_exists(api_client):
    tenant = TenantFactory()
    user = UserFactory(tenant=tenant, email="pix-update@example.com")
    _market_with_address(tenant)
    AsaasSubaccount.objects.create(
        tenant=tenant,
        name="Antigo",
        email="old@example.com",
        cpf_cnpj="12345678901",
        pix_key_type=AsaasSubaccount.PixKeyType.CPF,
        pix_key="12345678901",
        asaas_wallet_id="wal_existing",
        account_status=AsaasSubaccount.AccountStatus.APPROVED,
    )
    _auth(api_client, user)

    with mock.patch("apps.billing.services.asaas_subaccount.AsaasClient") as mock_cls:
        response = api_client.put(
            reverse("integrations-pix"),
            {**PIX_PAYLOAD, "name": "Nome Atualizado"},
            format="json",
        )

    assert response.status_code == 200
    assert response.json()["name"] == "Nome Atualizado"
    assert response.json()["asaas_wallet_id"] == "wal_existing"
    mock_cls.return_value.create_subaccount.assert_not_called()

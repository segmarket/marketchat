from decimal import Decimal
from unittest import mock

import pytest
from django.urls import reverse
from rest_framework_simplejwt.tokens import RefreshToken

from apps.financial.models import LedgerTransaction, Wallet, WithdrawalRequest
from tests.factories import TenantFactory, UserFactory


def _auth_client(api_client, user):
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(user).access_token}")
    return api_client


@pytest.mark.django_db
def test_financial_statement_returns_balance_and_ledger(api_client):
    tenant = TenantFactory()
    user = UserFactory(tenant=tenant, is_tenant_admin=True)
    wallet = Wallet.objects.create(
        tenant=tenant,
        balance_available=Decimal("49.00"),
        default_pix_key="mercado@example.com",
        default_pix_key_type="EMAIL",
    )
    LedgerTransaction.objects.create(
        wallet=wallet,
        amount=Decimal("49.00"),
        entry_type=LedgerTransaction.EntryType.INFLOW,
        description="Venda — teste",
        external_id="pay_stmt_1",
    )

    url = reverse("financial-statement")
    _auth_client(api_client, user)
    response = api_client.get(url)

    assert response.status_code == 200
    data = response.json()
    assert data["balance_available"] == "49.00"
    assert data["fee_percent"] == 2.0
    assert data["has_pix_key_configured"] is True
    assert data["default_pix_key"] == "mercado@example.com"
    assert len(data["results"]) == 1


@pytest.mark.django_db
@mock.patch("apps.financial.services.wallet.process_asaas_pix_transfer")
def test_financial_withdraw_automatic_transfer(mock_transfer, api_client):
    tenant = TenantFactory()
    user = UserFactory(tenant=tenant, is_tenant_admin=True)
    Wallet.objects.create(
        tenant=tenant,
        balance_available=Decimal("100.00"),
        default_pix_key="mercado@example.com",
        default_pix_key_type="EMAIL",
    )
    mock_transfer.return_value = {"id": "tra_api_1", "status": "DONE"}

    url = reverse("financial-withdraw")
    _auth_client(api_client, user)
    response = api_client.post(url, {"amount": "25.50"}, format="json")

    assert response.status_code == 201
    assert response.json()["status"] == WithdrawalRequest.Status.PAID
    wallet = Wallet.objects.get(tenant=tenant)
    assert wallet.balance_available == Decimal("74.50")
    assert wallet.balance_blocked == Decimal("0")


@pytest.mark.django_db
def test_financial_withdraw_requires_pix_key_configured(api_client):
    tenant = TenantFactory()
    user = UserFactory(tenant=tenant, is_tenant_admin=True)
    Wallet.objects.create(tenant=tenant, balance_available=Decimal("100.00"))

    url = reverse("financial-withdraw")
    _auth_client(api_client, user)
    response = api_client.post(url, {"amount": "10.00"}, format="json")

    assert response.status_code == 400
    assert "chave pix" in response.json()["detail"].lower()


@pytest.mark.django_db
def test_financial_wallet_settings_get_masks_configured_key(api_client):
    tenant = TenantFactory()
    user = UserFactory(tenant=tenant, is_tenant_admin=True)
    Wallet.objects.create(
        tenant=tenant,
        default_pix_key="mercado@example.com",
        default_pix_key_type="EMAIL",
    )

    url = reverse("financial-wallet-settings")
    _auth_client(api_client, user)
    response = api_client.get(url)

    assert response.status_code == 200
    data = response.json()
    assert data["has_pix_key_configured"] is True
    assert data["default_pix_key"] == ""
    assert data["default_pix_key_masked"] == "me***@example.com"
    assert data["default_pix_key_type"] == "EMAIL"


@pytest.mark.django_db
def test_financial_wallet_settings_patch_rejects_invalid_cpf(api_client):
    tenant = TenantFactory()
    user = UserFactory(tenant=tenant, is_tenant_admin=True)

    url = reverse("financial-wallet-settings")
    _auth_client(api_client, user)
    response = api_client.patch(
        url,
        {
            "default_pix_key_type": "CPF",
            "default_pix_key": "111.111.111-11",
        },
        format="json",
    )

    assert response.status_code == 400
    assert "default_pix_key" in response.json()


@pytest.mark.django_db
def test_financial_wallet_settings_patch_normalizes_valid_cpf(api_client):
    tenant = TenantFactory()
    user = UserFactory(tenant=tenant, is_tenant_admin=True)

    url = reverse("financial-wallet-settings")
    _auth_client(api_client, user)
    response = api_client.patch(
        url,
        {
            "default_pix_key_type": "CPF",
            "default_pix_key": "529.982.247-25",
        },
        format="json",
    )

    assert response.status_code == 200
    data = response.json()
    assert data["default_pix_key"] == "52998224725"
    assert data["has_pix_key_configured"] is True
    wallet = Wallet.objects.get(tenant=tenant)
    assert wallet.default_pix_key == "52998224725"


@pytest.mark.django_db
def test_financial_wallet_settings_patch(api_client):
    tenant = TenantFactory()
    user = UserFactory(tenant=tenant, is_tenant_admin=True)

    url = reverse("financial-wallet-settings")
    _auth_client(api_client, user)
    response = api_client.patch(
        url,
        {
            "default_pix_key_type": "EMAIL",
            "default_pix_key": "Mercado@Example.com",
        },
        format="json",
    )

    assert response.status_code == 200
    data = response.json()
    assert data["has_pix_key_configured"] is True
    assert data["default_pix_key"] == "mercado@example.com"
    wallet = Wallet.objects.get(tenant=tenant)
    assert wallet.default_pix_key_type == "EMAIL"


@pytest.mark.django_db
def test_financial_endpoints_require_tenant_admin(api_client):
    tenant = TenantFactory()
    user = UserFactory(tenant=tenant, is_tenant_admin=False)
    _auth_client(api_client, user)

    assert api_client.get(reverse("financial-statement")).status_code == 403
    assert api_client.post(reverse("financial-withdraw"), {}, format="json").status_code == 403
    assert api_client.get(reverse("financial-wallet-settings")).status_code == 403
    assert api_client.patch(reverse("financial-wallet-settings"), {}, format="json").status_code == 403

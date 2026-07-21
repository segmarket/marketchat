from decimal import Decimal
from unittest import mock

import pytest
from django.urls import reverse
from rest_framework_simplejwt.tokens import RefreshToken

from apps.sales.models import Cart, CartItem
from tests.factories import (
    ChatSessionFactory,
    MarketFactory,
    ResidentFactory,
    TenantFactory,
    UserFactory,
)


def _auth(client, user):
    client.credentials(
        HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(user).access_token}",
    )


@pytest.mark.django_db
@mock.patch("apps.billing.services.chat_pix_charge.AsaasClient")
def test_generate_chat_pix_with_items(mock_client_cls, api_client):
    tenant = TenantFactory()
    user = UserFactory(tenant=tenant, email="pix-chat@example.com")
    market = MarketFactory(tenant=tenant)
    resident = ResidentFactory(tenant=tenant, market=market, name="Ana")
    session = ChatSessionFactory(tenant=tenant, phone_number=resident.phone_number)

    client = mock_client_cls.return_value
    client.create_customer.return_value = {"id": "cus_123"}
    client.create_payment.return_value = {
        "id": "pay_abc",
        "billingType": "PIX",
        "invoiceUrl": "https://asaas.test/i/pay_abc",
        "pixCopiaECola": "",
    }
    client.get_payment_pix_qrcode.return_value = {
        "payload": "00020126580014BR.GOV.BCB.PIX0136fake-pix-code",
    }

    _auth(api_client, user)
    url = reverse("payments-generate-pix-chat")
    resp = api_client.post(
        url,
        {
            "session_id": session.id,
            "items": [
                {"name": "Refrigerante", "quantity": 2, "unit_price": "5.50"},
                {"name": "Salgadinho", "quantity": 1, "unit_price": "4.00"},
            ],
            "description": "Pedido balcão",
        },
        format="json",
    )
    assert resp.status_code == 201, resp.content
    data = resp.json()
    assert data["pix_copia_e_cola"].startswith("000201")
    assert data["invoice_url"] == "https://asaas.test/i/pay_abc"
    assert data["amount"] == "15.00"
    assert data["cart_id"]

    cart = Cart.objects.get(pk=data["cart_id"])
    assert cart.status == Cart.Status.AWAITING_PAYMENT
    assert cart.asaas_billing_id == "pay_abc"
    assert cart.items.count() == 2
    assert CartItem.objects.filter(cart=cart, product__isnull=True).count() == 2


@pytest.mark.django_db
@mock.patch("apps.billing.services.chat_pix_charge.AsaasClient")
def test_generate_chat_pix_amount_only(mock_client_cls, api_client):
    tenant = TenantFactory()
    user = UserFactory(tenant=tenant, email="pix-amount@example.com")
    market = MarketFactory(tenant=tenant)
    resident = ResidentFactory(tenant=tenant, market=market)
    session = ChatSessionFactory(tenant=tenant, phone_number=resident.phone_number)

    client = mock_client_cls.return_value
    client.create_customer.return_value = {"id": "cus_1"}
    client.create_payment.return_value = {
        "id": "pay_1",
        "billingType": "PIX",
        "invoiceUrl": "https://asaas.test/i/1",
        "pixCopiaECola": "PIXCODE123",
    }

    _auth(api_client, user)
    resp = api_client.post(
        reverse("payments-generate-pix-chat"),
        {"session_id": session.id, "amount": "29.90"},
        format="json",
    )
    assert resp.status_code == 201
    assert resp.json()["pix_copia_e_cola"] == "PIXCODE123"
    cart = Cart.objects.get(pk=resp.json()["cart_id"])
    item = cart.items.get()
    assert item.item_name == "Cobrança avulsa"
    assert item.quantity == 1
    assert item.unit_price == Decimal("29.90")


@pytest.mark.django_db
def test_generate_chat_pix_requires_resident(api_client):
    tenant = TenantFactory()
    user = UserFactory(tenant=tenant, email="pix-nores@example.com")
    session = ChatSessionFactory(tenant=tenant, phone_number="5511999990000")

    _auth(api_client, user)
    resp = api_client.post(
        reverse("payments-generate-pix-chat"),
        {"session_id": session.id, "amount": "10.00"},
        format="json",
    )
    assert resp.status_code == 400
    assert "Morador" in resp.json()["detail"]


@pytest.mark.django_db
def test_generate_chat_pix_invalid_payload(api_client):
    tenant = TenantFactory()
    user = UserFactory(tenant=tenant, email="pix-bad@example.com")
    _auth(api_client, user)
    resp = api_client.post(
        reverse("payments-generate-pix-chat"),
        {"session_id": 1},
        format="json",
    )
    assert resp.status_code == 400

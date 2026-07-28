from decimal import Decimal
from unittest import mock

import pytest
from django.urls import reverse
from rest_framework_simplejwt.tokens import RefreshToken

from apps.billing.services.chat_pix_whatsapp_copy import (
    build_chat_pix_code_message,
    build_chat_pix_summary_message,
)
from apps.billing.services.tenant_default_asaas_customer import (
    ensure_tenant_default_asaas_customer,
)
from apps.sales.models import Cart, CartItem
from tests.factories import (
    ChatSessionFactory,
    MarketFactory,
    ResidentFactory,
    TenantFactory,
    UserFactory,
    WhatsappInstanceFactory,
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
    assert data["billing_mode"] == "resident"
    assert data["message_pix"] == data["pix_copia_e_cola"]
    assert data["pix_copia_e_cola"] not in data["message_summary"]
    assert "mensagem abaixo" in data["message_summary"]

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
    assert resp.json()["billing_mode"] == "resident"
    cart = Cart.objects.get(pk=resp.json()["cart_id"])
    item = cart.items.get()
    assert item.item_name == "Cobrança avulsa"
    assert item.quantity == 1
    assert item.unit_price == Decimal("29.90")


@pytest.mark.django_db
@mock.patch("apps.billing.services.chat_pix_charge.AsaasClient")
def test_generate_chat_pix_walk_in_without_resident(mock_client_cls, api_client):
    tenant = TenantFactory(cpf_cnpj="11222333000181")
    tenant.asaas_default_customer_id = "cus_default"
    tenant.save(update_fields=["asaas_default_customer_id"])
    user = UserFactory(tenant=tenant, email="pix-walkin@example.com")
    phone = "5511999990000"
    session = ChatSessionFactory(tenant=tenant, phone_number=phone)

    client = mock_client_cls.return_value
    client.create_payment.return_value = {
        "id": "pay_wi",
        "billingType": "PIX",
        "invoiceUrl": "https://asaas.test/i/wi",
        "pixCopiaECola": "WALKINPIX",
    }

    _auth(api_client, user)
    resp = api_client.post(
        reverse("payments-generate-pix-chat"),
        {"session_id": session.id, "amount": "10.00"},
        format="json",
    )
    assert resp.status_code == 201, resp.content
    data = resp.json()
    assert data["billing_mode"] == "walk_in"
    assert data["pix_copia_e_cola"] == "WALKINPIX"
    assert phone in data["description"]
    assert "Venda Chat Avulso" in data["description"]
    client.create_customer.assert_not_called()
    client.create_payment.assert_called_once()
    assert client.create_payment.call_args[0][0]["customer"] == "cus_default"


@pytest.mark.django_db
def test_generate_chat_pix_walk_in_missing_default_customer(api_client):
    tenant = TenantFactory(cpf_cnpj="")
    user = UserFactory(tenant=tenant, email="pix-nodoc@example.com")
    session = ChatSessionFactory(tenant=tenant, phone_number="5511999990000")

    _auth(api_client, user)
    resp = api_client.post(
        reverse("payments-generate-pix-chat"),
        {"session_id": session.id, "amount": "10.00"},
        format="json",
    )
    assert resp.status_code == 400
    assert "CPF" in resp.json()["detail"] or "CNPJ" in resp.json()["detail"]


@pytest.mark.django_db
def test_chat_pix_whatsapp_copy_separates_payload():
    pix = "00020126580014BR.GOV.BCB.PIX0136fake"
    summary = build_chat_pix_summary_message(
        amount="15.00",
        invoice_url="https://asaas.test/pay",
        items_summary=[
            {"name": "Item", "quantity": 1, "unit_price": "15.00", "subtotal": "15.00"},
        ],
    )
    assert pix not in summary
    assert "https://asaas.test/pay" in summary
    assert "mensagem abaixo" in summary
    assert build_chat_pix_code_message(pix) == pix
    assert build_chat_pix_code_message(f"  {pix}  ") == pix


@pytest.mark.django_db
@mock.patch("apps.billing.services.chat_pix_whatsapp_delivery.pause_bot")
@mock.patch("apps.billing.services.chat_pix_whatsapp_delivery.log_agent_outbound")
@mock.patch("apps.billing.services.chat_pix_whatsapp_delivery.send_whatsapp_reply")
@mock.patch("apps.billing.services.chat_pix_charge.AsaasClient")
def test_generate_chat_pix_deliver_whatsapp_two_messages(
    mock_client_cls,
    mock_send,
    _mock_log,
    mock_pause,
    api_client,
):
    tenant = TenantFactory()
    WhatsappInstanceFactory(tenant=tenant, is_active=True)
    user = UserFactory(tenant=tenant, email="pix-deliver@example.com")
    market = MarketFactory(tenant=tenant)
    resident = ResidentFactory(tenant=tenant, market=market, name="Ana")
    session = ChatSessionFactory(tenant=tenant, phone_number=resident.phone_number)

    client = mock_client_cls.return_value
    client.create_customer.return_value = {"id": "cus_123"}
    client.create_payment.return_value = {
        "id": "pay_abc",
        "billingType": "PIX",
        "invoiceUrl": "https://asaas.test/i/pay_abc",
        "pixCopiaECola": "PIXONLYCODE",
    }

    _auth(api_client, user)
    resp = api_client.post(
        reverse("payments-generate-pix-chat"),
        {
            "session_id": session.id,
            "amount": "10.00",
            "deliver_whatsapp": True,
        },
        format="json",
    )
    assert resp.status_code == 201, resp.content
    data = resp.json()
    assert data["delivered_whatsapp"] is True
    assert mock_send.call_count == 2
    assert mock_send.call_args_list[0][0][2] == data["message_summary"]
    assert mock_send.call_args_list[1][0][2] == "PIXONLYCODE"
    mock_pause.assert_called_once()


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


@pytest.mark.django_db
@mock.patch("apps.billing.services.tenant_default_asaas_customer.AsaasClient")
def test_ensure_tenant_default_asaas_customer_creates_once(mock_client_cls):
    tenant = TenantFactory(cpf_cnpj="39053344705")
    client = mock_client_cls.return_value
    client.create_customer.return_value = {"id": "cus_cf"}

    cid = ensure_tenant_default_asaas_customer(tenant, client=client)
    assert cid == "cus_cf"
    tenant.refresh_from_db()
    assert tenant.asaas_default_customer_id == "cus_cf"
    body = client.create_customer.call_args[0][0]
    assert body["name"].startswith("Consumidor Final")
    assert body["cpfCnpj"] == "39053344705"

    client.create_customer.reset_mock()
    cid2 = ensure_tenant_default_asaas_customer(tenant, client=client)
    assert cid2 == "cus_cf"
    client.create_customer.assert_not_called()


@pytest.mark.django_db
@mock.patch("apps.markets.views._schedule_default_asaas_customer")
def test_market_create_schedules_default_customer(mock_schedule, api_client):
    tenant = TenantFactory()
    user = UserFactory(tenant=tenant, email="market-hook@example.com")
    _auth(api_client, user)

    resp = api_client.post(
        reverse("markets-list"),
        {"name": "Torre A", "address": "Rua 1"},
        format="json",
    )
    assert resp.status_code == 201
    mock_schedule.assert_called_once_with(tenant.id)


@pytest.mark.django_db
def test_provision_command_dry_run(capsys):
    tenant = TenantFactory(cpf_cnpj="39053344705")
    MarketFactory(tenant=tenant)
    from django.core.management import call_command

    call_command("provision_tenant_default_asaas_customers", "--dry-run")
    out = capsys.readouterr().out
    assert "dry-run" in out
    tenant.refresh_from_db()
    assert tenant.asaas_default_customer_id == ""

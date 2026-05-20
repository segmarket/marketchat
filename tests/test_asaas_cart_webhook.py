from decimal import Decimal
from unittest import mock

import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from apps.residents.models import ChatSession
from apps.sales.models import Cart
from apps.billing.services.asaas_webhook_payload import cart_external_reference
from apps.sales.services.asaas_payment_webhook import (
    process_cart_asaas_event,
    sync_cart_payment_from_asaas,
)
from tests.factories import (
    CartFactory,
    ChatSessionFactory,
    ResidentFactory,
    TenantFactory,
    WhatsappInstanceFactory,
)

WEBHOOK_URL = "/api/webhooks/asaas/"
BILLING_WEBHOOK_URL = "/api/billing/webhooks/asaas/"


def _payment_payload(*, event: str, payment_id: str) -> dict:
    return {
        "event": event,
        "payment": {"id": payment_id, "value": 25.50},
    }


@pytest.fixture
def cart_setup(db):
    tenant = TenantFactory()
    resident = ResidentFactory(
        tenant=tenant,
        name="Maria Silva",
        phone_number="5511999001122",
    )
    WhatsappInstanceFactory(tenant=tenant)
    cart = CartFactory(
        tenant=tenant,
        resident=resident,
        status=Cart.Status.AWAITING_PAYMENT,
        total_value=Decimal("25.50"),
        asaas_billing_id="pay_cart_abc123",
    )
    session = ChatSessionFactory(
        tenant=tenant,
        phone_number=resident.phone_number,
        state=ChatSession.State.AWAITING_PHOTO,
        active_cart=cart,
    )
    return tenant, resident, cart, session


@pytest.mark.django_db
@mock.patch("apps.sales.services.asaas_payment_webhook.send_whatsapp_reply")
def test_payment_received_completes_cart_and_unlocks_session(mock_send, cart_setup):
    _tenant, resident, cart, session = cart_setup

    assert process_cart_asaas_event(
        event="PAYMENT_RECEIVED",
        payment={"id": cart.asaas_billing_id},
    )

    cart.refresh_from_db()
    session.refresh_from_db()
    assert cart.status == Cart.Status.COMPLETED
    assert session.state == ChatSession.State.IDLE
    assert session.active_cart_id is None

    mock_send.assert_called_once()
    _instance, phone, text = mock_send.call_args[0]
    assert phone == resident.phone_number
    assert "PAGAMENTO CONFIRMADO" in text
    assert "Maria Silva" in text
    assert "R$ 25,50" in text


@pytest.mark.django_db
@mock.patch("apps.sales.services.asaas_payment_webhook.send_whatsapp_reply")
def test_payment_confirmed_alias_event(mock_send, cart_setup):
    _tenant, _resident, cart, _session = cart_setup

    process_cart_asaas_event(
        event="PAYMENT_CONFIRMED",
        payment={"id": cart.asaas_billing_id},
    )

    cart.refresh_from_db()
    assert cart.status == Cart.Status.COMPLETED
    mock_send.assert_called_once()


@pytest.mark.django_db
@mock.patch("apps.sales.services.asaas_payment_webhook.send_whatsapp_reply")
def test_payment_overdue_expires_cart(mock_send, cart_setup):
    _tenant, resident, cart, session = cart_setup

    process_cart_asaas_event(
        event="PAYMENT_OVERDUE",
        payment={"id": cart.asaas_billing_id},
    )

    cart.refresh_from_db()
    session.refresh_from_db()
    assert cart.status == Cart.Status.EXPIRED
    assert session.state == ChatSession.State.IDLE

    mock_send.assert_called_once()
    text = mock_send.call_args[0][2]
    assert "PIX EXPIRADO" in text
    assert "R$ 25,50" in text
    assert resident.phone_number == mock_send.call_args[0][1]


@pytest.mark.django_db
@mock.patch("apps.sales.services.asaas_payment_webhook.send_whatsapp_reply")
def test_payment_deleted_cancels_cart(mock_send, cart_setup):
    _tenant, _resident, cart, session = cart_setup

    process_cart_asaas_event(
        event="PAYMENT_DELETED",
        payment={"id": cart.asaas_billing_id},
    )

    cart.refresh_from_db()
    session.refresh_from_db()
    assert cart.status == Cart.Status.CANCELLED
    assert session.state == ChatSession.State.IDLE
    mock_send.assert_called_once()


@pytest.mark.django_db
@mock.patch("apps.billing.services.webhook_processor.process_cart_asaas_event")
@mock.patch("apps.billing.services.webhook_processor._process_subscription_webhook")
def test_webhook_endpoint_routes_cart_before_subscription(
    mock_sub,
    mock_cart,
    api_client: APIClient,
):
    mock_cart.return_value = True
    response = api_client.post(
        WEBHOOK_URL,
        _payment_payload(event="PAYMENT_RECEIVED", payment_id="pay_x"),
        format="json",
    )
    assert response.status_code == 200
    mock_cart.assert_called_once()
    mock_sub.assert_not_called()


@pytest.mark.django_db
@mock.patch("apps.sales.services.asaas_payment_webhook.send_whatsapp_reply")
def test_webhook_http_post_public_url(mock_send, cart_setup, api_client: APIClient):
    _tenant, _resident, cart, _session = cart_setup

    response = api_client.post(
        WEBHOOK_URL,
        _payment_payload(event="PAYMENT_RECEIVED", payment_id=cart.asaas_billing_id),
        format="json",
    )
    assert response.status_code == 200
    mock_send.assert_called_once()


@pytest.mark.django_db
@mock.patch("apps.sales.services.asaas_payment_webhook.send_whatsapp_reply")
def test_billing_webhook_url_still_works(mock_send, cart_setup, api_client: APIClient):
    _tenant, _resident, cart, _session = cart_setup

    response = api_client.post(
        BILLING_WEBHOOK_URL,
        _payment_payload(event="PAYMENT_RECEIVED", payment_id=cart.asaas_billing_id),
        format="json",
    )
    assert response.status_code == 200
    mock_send.assert_called_once()


@pytest.mark.django_db
def test_webhook_rejects_invalid_token_when_verify_enabled(settings, api_client: APIClient):
    settings.ASAAS_WEBHOOK_VERIFY = True
    settings.ASAAS_WEBHOOK_TOKEN = "secret-token"

    response = api_client.post(
        WEBHOOK_URL,
        _payment_payload(event="PAYMENT_RECEIVED", payment_id="pay_x"),
        format="json",
        HTTP_X_WEBHOOK_TOKEN="wrong",
    )
    assert response.status_code == 401


@pytest.mark.django_db
@mock.patch("apps.sales.services.asaas_payment_webhook.send_whatsapp_reply")
def test_payment_received_idempotent(mock_send, cart_setup):
    _tenant, _resident, cart, _session = cart_setup
    cart.status = Cart.Status.COMPLETED
    cart.save(update_fields=["status"])

    assert not process_cart_asaas_event(
        event="PAYMENT_RECEIVED",
        payment={"id": cart.asaas_billing_id},
    )
    mock_send.assert_not_called()


@pytest.mark.django_db
@mock.patch("apps.sales.services.asaas_payment_webhook.send_whatsapp_reply")
def test_payment_found_by_external_reference(mock_send, cart_setup):
    _tenant, _resident, cart, _session = cart_setup
    cart.asaas_billing_id = ""
    cart.save(update_fields=["asaas_billing_id"])

    assert process_cart_asaas_event(
        event="PAYMENT_CONFIRMED",
        payment={
            "id": "pay_sandbox_new",
            "externalReference": cart_external_reference(cart.id),
        },
    )

    cart.refresh_from_db()
    assert cart.status == Cart.Status.COMPLETED
    assert cart.asaas_billing_id == "pay_sandbox_new"
    mock_send.assert_called_once()


@pytest.mark.django_db
@mock.patch("apps.sales.services.asaas_payment_webhook.send_whatsapp_reply")
@mock.patch("apps.sales.services.asaas_payment_webhook.AsaasClient")
def test_sync_cart_payment_from_asaas_api(mock_client_cls, mock_send, cart_setup):
    _tenant, _resident, cart, _session = cart_setup
    mock_client_cls.return_value.get_payment.return_value = {
        "id": cart.asaas_billing_id,
        "status": "RECEIVED",
    }

    assert sync_cart_payment_from_asaas(cart) is True

    cart.refresh_from_db()
    assert cart.status == Cart.Status.COMPLETED
    mock_send.assert_called_once()


@pytest.mark.django_db
def test_cleanup_expired_carts_command(cart_setup):
    _tenant, resident, cart, session = cart_setup
    Cart.objects.filter(pk=cart.pk).update(
        status=Cart.Status.AWAITING_PAYMENT,
        created_at=timezone.now() - timezone.timedelta(minutes=20),
    )
    session.state = ChatSession.State.AWAITING_PHOTO
    session.active_cart = cart
    session.save(update_fields=["state", "active_cart"])

    from django.core.management import call_command

    call_command("cleanup_expired_carts")

    cart.refresh_from_db()
    session.refresh_from_db()
    assert cart.status == Cart.Status.CANCELLED
    assert session.state == ChatSession.State.IDLE
    assert session.active_cart_id is None

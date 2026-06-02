from unittest import mock

import pytest
from django.core.cache import cache
from django.urls import reverse
from rest_framework_simplejwt.tokens import RefreshToken

from tests.factories import SubscriptionFactory, TenantFactory, UserFactory

_PAYMENT_FIXTURE = {
    "data": [
        {
            "dueDate": "2026-05-10",
            "value": 29.9,
            "status": "RECEIVED",
            "billingType": "CREDIT_CARD",
            "invoiceUrl": "https://asaas.com/i/1",
        },
        {
            "dueDate": "2026-06-10",
            "value": 29.9,
            "status": "PENDING",
            "billingType": "CREDIT_CARD",
            "invoiceUrl": "https://asaas.com/i/2",
        },
    ],
}


def _auth_client(api_client, user):
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(user).access_token}")
    return api_client


@pytest.mark.django_db
def test_billing_history_maps_and_caches(api_client):
    cache.clear()
    sub = SubscriptionFactory(asaas_customer_id="cus_hist_1")
    user = UserFactory(tenant=sub.tenant, email="billing@example.com")
    url = reverse("settings-billing-history")

    with mock.patch("apps.billing.services.billing_history.AsaasClient") as mock_cls:
        inst = mock_cls.return_value
        inst.list_payments.return_value = _PAYMENT_FIXTURE
        _auth_client(api_client, user)
        r1 = api_client.get(url)
        r2 = api_client.get(url)

    assert r1.status_code == 200
    results = r1.json()["results"]
    assert len(results) == 2
    assert results[0]["status"] == "PENDING"
    assert results[0]["due_date"] == "2026-06-10"
    assert results[1]["status"] == "PAID"
    assert results[1]["invoice_url"] == "https://asaas.com/i/1"
    inst.list_payments.assert_called_once_with(customer="cus_hist_1", limit=100)
    assert r2.status_code == 200


@pytest.mark.django_db
def test_billing_history_works_when_redis_unavailable(api_client):
    sub = SubscriptionFactory(asaas_customer_id="cus_hist_redis")
    user = UserFactory(tenant=sub.tenant, email="billing-redis@example.com")
    url = reverse("settings-billing-history")

    with mock.patch("apps.billing.services.billing_history.AsaasClient") as mock_cls:
        inst = mock_cls.return_value
        inst.list_payments.return_value = _PAYMENT_FIXTURE
        with mock.patch(
            "apps.billing.services.billing_history.cache.get",
            side_effect=OSError("redis down"),
        ):
            _auth_client(api_client, user)
            response = api_client.get(url)

    assert response.status_code == 200
    assert len(response.json()["results"]) == 2
    inst.list_payments.assert_called_once()


@pytest.mark.django_db
def test_billing_history_non_admin_forbidden(api_client):
    sub = SubscriptionFactory()
    user = UserFactory(tenant=sub.tenant, email="member@example.com", is_tenant_admin=False)
    url = reverse("settings-billing-history")
    _auth_client(api_client, user)
    response = api_client.get(url)
    assert response.status_code == 403


@pytest.mark.django_db
def test_payment_method_get_credit_card(api_client):
    sub = SubscriptionFactory(asaas_subscription_id="sub_pm_1")
    user = UserFactory(tenant=sub.tenant, email="pm@example.com")
    url = reverse("settings-billing-payment-method")

    with mock.patch("apps.billing.services.payment_method.AsaasClient") as mock_cls:
        mock_cls.return_value.get_subscription.return_value = {
            "billingType": "CREDIT_CARD",
            "creditCardBrand": "MASTERCARD",
            "creditCardNumber": "************4321",
        }
        _auth_client(api_client, user)
        response = api_client.get(url)

    assert response.status_code == 200
    data = response.json()
    assert data["billing_type"] == "CREDIT_CARD"
    assert data["card_last_four"] == "4321"
    assert "4321" in data["display_label"]


@pytest.mark.django_db
def test_payment_method_post_updates_card(api_client):
    cache.clear()
    sub = SubscriptionFactory(asaas_customer_id="cus_upd_1", asaas_subscription_id="sub_upd_1")
    user = UserFactory(tenant=sub.tenant, email="upd@example.com")
    url = reverse("settings-billing-payment-method")
    payload = {
        "credit_card": {
            "holderName": "TEST USER",
            "number": "5162306219378829",
            "expiryMonth": "12",
            "expiryYear": "2030",
            "ccv": "123",
        },
        "credit_card_holder": {
            "name": "Test User",
            "email": "upd@example.com",
            "postalCode": "01311000",
            "address": "Av Paulista",
            "addressNumber": "1000",
            "province": "SP",
            "phone": "11999999999",
        },
    }

    with mock.patch("apps.billing.services.payment_method.AsaasClient") as mock_cls:
        inst = mock_cls.return_value
        inst.tokenize_credit_card.return_value = {"creditCardToken": "tok_new"}
        inst.update_subscription_credit_card.return_value = {}
        inst.get_subscription.return_value = {
            "billingType": "CREDIT_CARD",
            "creditCardBrand": "VISA",
            "creditCardNumber": "************9999",
        }
        _auth_client(api_client, user)
        response = api_client.post(url, payload, format="json")

    assert response.status_code == 200
    inst.tokenize_credit_card.assert_called_once()
    inst.update_subscription_credit_card.assert_called_once()
    assert response.json()["card_last_four"] == "9999"

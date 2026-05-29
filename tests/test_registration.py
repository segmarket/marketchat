from unittest import mock

import pytest
from django.urls import reverse

from apps.accounts.models import User
from apps.billing.models import Subscription
from apps.tenants.models import Tenant


def _asaas_mock():
    patcher = mock.patch("apps.billing.services.subscription_flow.AsaasClient")
    mock_cls = patcher.start()
    inst = mock_cls.return_value
    inst.create_customer.return_value = {"id": "cus_test_1"}
    inst.tokenize_credit_card.return_value = {"creditCardToken": "tok_test_1"}
    inst.create_subscription.return_value = {"id": "sub_test_1", "status": "ACTIVE"}
    return patcher, inst


@pytest.mark.django_db
def test_register_client_success(api_client):
    url = reverse("auth-register")
    payload = {
        "company_name": "Acme Ltda",
        "tenant_slug": "acme-test",
        "admin_email": "admin@acme.com",
        "admin_password": "StrongPass123!",
        "first_name": "Ada",
        "last_name": "Lovelace",
        "credit_card": {
            "holderName": "ADA LOVELACE",
            "number": "5162306219378829",
            "expiryMonth": "12",
            "expiryYear": "2030",
            "ccv": "123",
        },
        "credit_card_holder": {
            "name": "Ada Lovelace",
            "email": "admin@acme.com",
            "cpfCnpj": "24971563792",
            "postalCode": "01311000",
            "address": "Av Paulista",
            "addressNumber": "1000",
            "province": "SP",
            "phone": "11999999999",
        },
    }
    patcher, _ = _asaas_mock()
    try:
        response = api_client.post(url, payload, format="json")
    finally:
        patcher.stop()
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "admin@acme.com"
    assert User.objects.filter(email="admin@acme.com").exists()
    tenant = Tenant.objects.get(slug="acme-test")
    assert tenant.cpf_cnpj == "24971563792"
    assert tenant.phone == "11999999999"
    assert Subscription.objects.filter(asaas_subscription_id="sub_test_1").exists()


@pytest.mark.django_db
def test_register_persists_attribution(api_client):
    url = reverse("auth-register")
    payload = {
        "company_name": "Ads Co",
        "tenant_slug": "ads-co",
        "admin_email": "ads@example.com",
        "admin_password": "StrongPass123!",
        "first_name": "Ana",
        "last_name": "Ads",
        "attribution": {
            "utm_source": "google",
            "utm_medium": "cpc",
            "utm_campaign": "trial_br",
            "gclid": "gclid_test_abc",
        },
        "credit_card": {
            "holderName": "ANA ADS",
            "number": "5162306219378829",
            "expiryMonth": "12",
            "expiryYear": "2030",
            "ccv": "123",
        },
        "credit_card_holder": {
            "name": "Ana Ads",
            "email": "ads@example.com",
            "cpfCnpj": "24971563792",
            "postalCode": "01311000",
            "address": "Av Paulista",
            "addressNumber": "1000",
            "province": "SP",
            "phone": "11999999999",
        },
    }
    patcher, _ = _asaas_mock()
    try:
        response = api_client.post(url, payload, format="json")
    finally:
        patcher.stop()
    assert response.status_code == 201
    tenant = Tenant.objects.get(slug="ads-co")
    assert tenant.utm_source == "google"
    assert tenant.utm_medium == "cpc"
    assert tenant.utm_campaign == "trial_br"
    assert tenant.gclid == "gclid_test_abc"
    assert tenant.fbclid == ""


@pytest.mark.django_db
def test_register_rejects_duplicate_email(api_client):
    url = reverse("auth-register")
    base_payload = {
        "company_name": "Dup",
        "tenant_slug": "dup-a",
        "admin_email": "dup@example.com",
        "admin_password": "StrongPass123!",
        "credit_card": {
            "holderName": "X",
            "number": "5162306219378829",
            "expiryMonth": "12",
            "expiryYear": "2030",
            "ccv": "123",
        },
        "credit_card_holder": {
            "name": "X",
            "email": "dup@example.com",
            "postalCode": "01311000",
            "address": "Rua A",
            "addressNumber": "1",
            "province": "SP",
            "phone": "11999999999",
        },
    }
    patcher, inst = _asaas_mock()
    try:
        r1 = api_client.post(url, {**base_payload, "tenant_slug": "dup-a"}, format="json")
        assert r1.status_code == 201
        inst.create_customer.return_value = {"id": "cus_test_2"}
        inst.tokenize_credit_card.return_value = {"creditCardToken": "tok_test_2"}
        inst.create_subscription.return_value = {"id": "sub_test_2", "status": "ACTIVE"}
        r2 = api_client.post(url, {**base_payload, "tenant_slug": "dup-b"}, format="json")
    finally:
        patcher.stop()
    assert r2.status_code == 400

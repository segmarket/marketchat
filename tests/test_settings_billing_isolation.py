from unittest import mock

import pytest
from django.urls import reverse
from rest_framework_simplejwt.tokens import RefreshToken

from tests.factories import SubscriptionFactory, UserFactory


@pytest.mark.django_db
def test_billing_history_uses_only_own_customer_id(api_client):
    sub_a = SubscriptionFactory(asaas_customer_id="cus_tenant_a")
    sub_b = SubscriptionFactory(asaas_customer_id="cus_tenant_b")
    user_a = UserFactory(tenant=sub_a.tenant, email="tenant_a@example.com")
    user_b = UserFactory(tenant=sub_b.tenant, email="tenant_b@example.com")
    url = reverse("settings-billing-history")

    payments_by_customer = {
        "cus_tenant_a": {
            "data": [
                {
                    "dueDate": "2026-05-01",
                    "value": 10.0,
                    "status": "RECEIVED",
                    "billingType": "CREDIT_CARD",
                    "invoiceUrl": "https://asaas.com/a",
                },
            ],
        },
        "cus_tenant_b": {
            "data": [
                {
                    "dueDate": "2026-05-02",
                    "value": 99.0,
                    "status": "RECEIVED",
                    "billingType": "BOLETO",
                    "invoiceUrl": "https://asaas.com/b",
                },
            ],
        },
    }

    def list_payments_side_effect(**kwargs):
        customer = kwargs.get("customer")
        return payments_by_customer[customer]

    with mock.patch("apps.billing.services.billing_history.AsaasClient") as mock_cls:
        mock_cls.return_value.list_payments.side_effect = list_payments_side_effect

        api_client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(user_a).access_token}",
        )
        response_a = api_client.get(url)
        assert response_a.status_code == 200
        results_a = response_a.json()["results"]
        assert len(results_a) == 1
        assert results_a[0]["value"] == 10.0
        assert results_a[0]["invoice_url"] == "https://asaas.com/a"

        mock_cls.return_value.list_payments.reset_mock()

        api_client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(user_b).access_token}",
        )
        response_b = api_client.get(url)
        assert response_b.status_code == 200
        results_b = response_b.json()["results"]
        assert len(results_b) == 1
        assert results_b[0]["value"] == 99.0

        mock_cls.return_value.list_payments.assert_called_with(customer="cus_tenant_b", limit=100)

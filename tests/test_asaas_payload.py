from datetime import datetime
from unittest import mock
from zoneinfo import ZoneInfo

import pytest
from django.test import override_settings

from apps.accounts.models import User
from apps.billing.services.subscription_flow import create_trial_subscription
from apps.tenants.models import Tenant


@pytest.mark.django_db
@override_settings(TRIAL_DAYS=7)
def test_asaas_subscription_payload_credit_card_and_first_due_plus_7():
    fixed_now = datetime(2026, 5, 12, 10, 0, 0, tzinfo=ZoneInfo("America/Sao_Paulo"))
    tenant = Tenant.objects.create(
        name="T",
        slug="t-payload",
        trial_ends_at=fixed_now,
    )
    user = User.objects.create_user("u@example.com", password="x", tenant=tenant)

    with mock.patch("apps.billing.services.subscription_flow.AsaasClient") as mock_cls:
        inst = mock_cls.return_value
        inst.create_customer.return_value = {"id": "cus_x"}
        inst.tokenize_credit_card.return_value = {"creditCardToken": "tok_x"}
        inst.create_subscription.return_value = {"id": "sub_x", "status": "ACTIVE"}
        with mock.patch("django.utils.timezone.now", return_value=fixed_now):
            create_trial_subscription(
                tenant,
                user,
                {
                    "holderName": "H",
                    "number": "4111111111111111",
                    "expiryMonth": "12",
                    "expiryYear": "2030",
                    "ccv": "123",
                },
                {
                    "name": "H",
                    "email": "u@example.com",
                    "postalCode": "01000",
                    "address": "Rua",
                    "addressNumber": "1",
                    "province": "SP",
                    "phone": "11999999999",
                },
                "203.0.113.1",
            )
        token_payload = inst.tokenize_credit_card.call_args[0][0]
        assert token_payload["customer"] == "cus_x"
        assert token_payload["remoteIp"] == "203.0.113.1"
        assert token_payload["creditCardHolderInfo"]["email"] == "u@example.com"

        payload = inst.create_subscription.call_args[0][0]
        assert payload["billingType"] == "CREDIT_CARD"
        assert payload["nextDueDate"] == "2026-05-19"
        assert payload["creditCardToken"] == "tok_x"

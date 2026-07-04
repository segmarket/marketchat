from __future__ import annotations

import hashlib
from unittest import mock

import pytest

from apps.billing.services import meta_capi
from apps.billing.services.meta_capi import (
    schedule_meta_purchase_event,
    send_meta_purchase_event,
)
from apps.billing.services.webhook_processor import process_asaas_webhook_payload
from apps.tenants.models import Tenant
from tests.factories import SubscriptionFactory, TenantFactory, UserFactory


def test_send_meta_purchase_noop_without_credentials(settings):
    settings.META_PIXEL_ID = ""
    settings.META_ACCESS_TOKEN = ""
    with mock.patch("apps.billing.services.meta_capi.requests.post") as post:
        send_meta_purchase_event("a@b.com", "11999999999", 59.9, event_id="pay_1")
    post.assert_not_called()


def test_send_meta_purchase_posts_hashed_user_data(settings):
    settings.META_PIXEL_ID = "pixel_test"
    settings.META_ACCESS_TOKEN = "token_test"

    email = "Admin@Example.com"
    phone = "11999998888"
    expected_em = hashlib.sha256(email.strip().lower().encode()).hexdigest()
    expected_ph = hashlib.sha256(f"55{phone}".encode()).hexdigest()

    mock_resp = mock.Mock()
    mock_resp.status_code = 200
    mock_resp.text = "{}"

    with mock.patch("apps.billing.services.meta_capi.requests.post", return_value=mock_resp) as post:
        send_meta_purchase_event(email, phone, 119.8, currency="BRL", event_id="pay_abc")

    post.assert_called_once()
    args, kwargs = post.call_args
    assert "pixel_test/events" in args[0]
    assert kwargs["params"]["access_token"] == "token_test"
    payload = kwargs["json"]["data"][0]
    assert payload["event_name"] == "Purchase"
    assert payload["event_id"] == "pay_abc"
    assert payload["custom_data"]["value"] == 119.8
    assert payload["custom_data"]["currency"] == "BRL"
    assert payload["user_data"]["em"] == [expected_em]
    assert payload["user_data"]["ph"] == [expected_ph]


def test_send_meta_purchase_swallows_network_errors(settings):
    settings.META_PIXEL_ID = "pixel_test"
    settings.META_ACCESS_TOKEN = "token_test"
    with mock.patch(
        "apps.billing.services.meta_capi.requests.post",
        side_effect=meta_capi.requests.RequestException("timeout"),
    ):
        send_meta_purchase_event("a@b.com", "11999999999", 10.0)


def test_schedule_meta_purchase_does_not_raise(settings):
    settings.META_PIXEL_ID = "pixel_test"
    settings.META_ACCESS_TOKEN = "token_test"

    with mock.patch("apps.billing.services.meta_capi.send_meta_purchase_event") as send:
        with mock.patch("apps.billing.services.meta_capi.transaction.on_commit", side_effect=lambda fn: fn()):
            with mock.patch("apps.billing.services.meta_capi.threading.Thread") as thread_cls:
                thread_cls.return_value.start = mock.Mock()
                schedule_meta_purchase_event("a@b.com", "11999999999", 59.9, event_id="pay_x")
                thread_cls.assert_called_once()
                target = thread_cls.call_args.kwargs["target"]
                target()
                send.assert_called_once()


@pytest.mark.django_db
def test_payment_received_schedules_meta_purchase():
    tenant = TenantFactory(
        subscription_status=Tenant.SubscriptionStatus.TRIAL,
        phone="11988887777",
    )
    sub = SubscriptionFactory(tenant=tenant)
    UserFactory(tenant=tenant, email="owner@meta.test", phone="11988887777", is_tenant_admin=True)

    with mock.patch(
        "apps.billing.services.webhook_processor.schedule_meta_purchase_event",
    ) as schedule:
        process_asaas_webhook_payload(
            {
                "event": "PAYMENT_RECEIVED",
                "payment": {
                    "id": "pay_meta_1",
                    "subscription": sub.asaas_subscription_id,
                    "value": 59.9,
                },
            },
        )

    schedule.assert_called_once()
    args, kwargs = schedule.call_args
    assert args[0] == "owner@meta.test"
    assert args[1] == "11988887777"
    assert args[2] == 59.9
    assert kwargs["event_id"] == "pay_meta_1"
    assert kwargs["currency"] == "BRL"

    tenant.refresh_from_db()
    assert tenant.subscription_status == Tenant.SubscriptionStatus.ACTIVE

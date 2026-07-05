from __future__ import annotations

import hashlib
from unittest import mock

import pytest

from apps.billing.services import facebook_capi
from apps.billing.services.facebook_capi import (
    FacebookCAPI,
    schedule_facebook_capi_event,
)


def test_send_event_noop_without_credentials(settings):
    settings.META_PIXEL_ID = ""
    settings.META_ACCESS_TOKEN = ""
    with mock.patch("apps.billing.services.facebook_capi.requests.post") as post:
        ok = FacebookCAPI().send_event("StartTrial", "a@b.com", "11999999999")
    assert ok is False
    post.assert_not_called()


def test_send_event_posts_hashed_user_data(settings):
    settings.META_PIXEL_ID = "pixel_test"
    settings.META_ACCESS_TOKEN = "token_test"

    email = "Admin@Example.com"
    phone = "11999998888"
    expected_em = hashlib.sha256(email.strip().lower().encode()).hexdigest()
    expected_ph = hashlib.sha256(f"55{phone}".encode()).hexdigest()

    mock_resp = mock.Mock()
    mock_resp.status_code = 200
    mock_resp.text = "{}"

    with mock.patch(
        "apps.billing.services.facebook_capi.requests.post",
        return_value=mock_resp,
    ) as post:
        ok = FacebookCAPI().send_event(
            "StartTrial",
            email,
            phone,
            custom_data={"value": 59.9, "currency": "BRL"},
            event_id="start_trial_tenant_42",
        )

    assert ok is True
    post.assert_called_once()
    args, kwargs = post.call_args
    assert "v20.0/pixel_test/events" in args[0]
    assert kwargs["params"]["access_token"] == "token_test"
    payload = kwargs["json"]["data"][0]
    assert payload["event_name"] == "StartTrial"
    assert payload["event_id"] == "start_trial_tenant_42"
    assert payload["custom_data"]["value"] == 59.9
    assert payload["custom_data"]["currency"] == "BRL"
    assert payload["user_data"]["em"] == [expected_em]
    assert payload["user_data"]["ph"] == [expected_ph]


def test_send_event_swallows_network_errors(settings):
    settings.META_PIXEL_ID = "pixel_test"
    settings.META_ACCESS_TOKEN = "token_test"
    with mock.patch(
        "apps.billing.services.facebook_capi.requests.post",
        side_effect=facebook_capi.requests.RequestException("timeout"),
    ):
        ok = FacebookCAPI().send_event("StartTrial", "a@b.com", "11999999999")
    assert ok is False


def test_schedule_facebook_capi_event_does_not_raise(settings):
    settings.META_PIXEL_ID = "pixel_test"
    settings.META_ACCESS_TOKEN = "token_test"

    with mock.patch.object(FacebookCAPI, "send_event") as send:
        with mock.patch(
            "apps.billing.services.facebook_capi.transaction.on_commit",
            side_effect=lambda fn: fn(),
        ):
            with mock.patch("apps.billing.services.facebook_capi.threading.Thread") as thread_cls:
                thread_cls.return_value.start = mock.Mock()
                schedule_facebook_capi_event(
                    event_name="StartTrial",
                    user_email="a@b.com",
                    user_phone="11999999999",
                    custom_data={"value": 59.9, "currency": "BRL"},
                    event_id="start_trial_tenant_1",
                )
                thread_cls.assert_called_once()
                target = thread_cls.call_args.kwargs["target"]
                target()
                send.assert_called_once()

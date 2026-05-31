from unittest import mock

import pytest

from apps.billing.models import AsaasSubaccount
from apps.billing.services.asaas_account_status import (
    apply_asaas_account_status_block,
    map_general_to_account_status,
    process_subaccount_status_webhook,
)
from tests.factories import AsaasSubaccountFactory, TenantFactory

WEBHOOK_URL = "/api/billing/webhooks/asaas/"


@pytest.mark.parametrize(
    ("general", "expected"),
    [
        ("APPROVED", AsaasSubaccount.AccountStatus.APPROVED),
        ("REJECTED", AsaasSubaccount.AccountStatus.REJECTED),
        ("AWAITING_APPROVAL", AsaasSubaccount.AccountStatus.PENDING),
        ("PENDING", AsaasSubaccount.AccountStatus.PENDING),
    ],
)
def test_map_general_to_account_status(general, expected):
    assert map_general_to_account_status(general) == expected


@pytest.mark.django_db
def test_apply_asaas_account_status_block_approves():
    sub = AsaasSubaccountFactory(
        account_status=AsaasSubaccount.AccountStatus.PENDING,
        asaas_account_id="acc-uuid-1",
    )
    apply_asaas_account_status_block(
        sub,
        {
            "general": "APPROVED",
            "commercialInfo": "APPROVED",
            "documentation": "APPROVED",
            "bankAccountInfo": "APPROVED",
        },
    )
    sub.refresh_from_db()
    assert sub.account_status == AsaasSubaccount.AccountStatus.APPROVED
    assert sub.asaas_status_general == "APPROVED"
    assert sub.status_synced_at is not None


@pytest.mark.django_db
def test_process_subaccount_status_webhook_by_account_id():
    sub = AsaasSubaccountFactory(asaas_account_id="acc-webhook-99")
    handled = process_subaccount_status_webhook(
        event="ACCOUNT_STATUS_GENERAL_APPROVAL_APPROVED",
        payload={
            "account": {"id": "acc-webhook-99"},
            "accountStatus": {
                "general": "APPROVED",
                "commercialInfo": "APPROVED",
                "documentation": "APPROVED",
                "bankAccountInfo": "APPROVED",
            },
        },
    )
    assert handled is True
    sub.refresh_from_db()
    assert sub.account_status == AsaasSubaccount.AccountStatus.APPROVED


@pytest.mark.django_db
def test_webhook_account_status_endpoint(api_client, settings):
    settings.ASAAS_WEBHOOK_VERIFY = True
    settings.ASAAS_WEBHOOK_TOKEN = "secret-token"
    sub = AsaasSubaccountFactory(asaas_account_id="acc-http-1")

    response = api_client.post(
        WEBHOOK_URL,
        {
            "event": "ACCOUNT_STATUS_GENERAL_APPROVAL_APPROVED",
            "account": {"id": "acc-http-1"},
            "accountStatus": {"general": "APPROVED"},
        },
        format="json",
        HTTP_X_WEBHOOK_TOKEN="secret-token",
    )
    assert response.status_code == 200
    sub.refresh_from_db()
    assert sub.account_status == AsaasSubaccount.AccountStatus.APPROVED


@pytest.mark.django_db
def test_sync_subaccount_status_from_asaas():
    sub = AsaasSubaccountFactory(
        asaas_subaccount_api_key="$aact_sub_test",
        account_status=AsaasSubaccount.AccountStatus.PENDING,
    )
    with mock.patch("apps.billing.services.asaas_account_status.AsaasClient") as mock_cls:
        mock_cls.return_value.get_my_account_status.return_value = {
            "general": "APPROVED",
            "commercialInfo": "APPROVED",
            "documentation": "AWAITING_APPROVAL",
            "bankAccountInfo": "APPROVED",
        }
        from apps.billing.services.asaas_account_status import sync_subaccount_status_from_asaas

        assert sync_subaccount_status_from_asaas(sub) is True

    sub.refresh_from_db()
    assert sub.account_status == AsaasSubaccount.AccountStatus.APPROVED

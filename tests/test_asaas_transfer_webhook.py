from decimal import Decimal
from unittest import mock

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from apps.billing.services.webhook_processor import process_asaas_webhook_payload
from apps.financial.models import LedgerTransaction, Wallet, WithdrawalRequest
from apps.financial.services.asaas_transfer_webhook import process_transfer_asaas_event
from tests.factories import TenantFactory

BILLING_WEBHOOK_URL = "/api/billing/webhooks/asaas/"


def _transfer_payload(
    *,
    event: str,
    transfer_id: str,
    status: str = "DONE",
    external_reference: str = "marketchat-withdraw-abc123",
) -> dict:
    return {
        "event": event,
        "transfer": {
            "id": transfer_id,
            "status": status,
            "value": 16.03,
            "operationType": "PIX",
            "description": "Saque MarketChat",
            "externalReference": external_reference,
        },
    }


@pytest.mark.django_db
def test_transfer_done_marks_withdrawal_paid():
    tenant = TenantFactory()
    wallet = Wallet.objects.create(
        tenant=tenant,
        balance_available=Decimal("0.00"),
    )
    ledger = LedgerTransaction.objects.create(
        wallet=wallet,
        amount=Decimal("16.03"),
        entry_type=LedgerTransaction.EntryType.OUTFLOW,
        description="Saque Pix",
        external_id="591483b2-7ea8-45ec-a688-6eaf1fd068ac",
    )
    withdrawal = WithdrawalRequest.objects.create(
        wallet=wallet,
        amount=Decimal("16.03"),
        pix_key="38113982884",
        pix_key_type="CPF",
        status=WithdrawalRequest.Status.PROCESSING,
        asaas_transfer_id="591483b2-7ea8-45ec-a688-6eaf1fd068ac",
        ledger_transaction=ledger,
    )

    handled = process_transfer_asaas_event(
        event="TRANSFER_DONE",
        payload=_transfer_payload(
            event="TRANSFER_DONE",
            transfer_id="591483b2-7ea8-45ec-a688-6eaf1fd068ac",
        ),
    )

    assert handled is True
    withdrawal.refresh_from_db()
    assert withdrawal.status == WithdrawalRequest.Status.PAID
    assert withdrawal.processed_at is not None
    assert Wallet.objects.get(pk=wallet.pk).balance_available == Decimal("0.00")


@pytest.mark.django_db
def test_transfer_done_is_idempotent():
    tenant = TenantFactory()
    wallet = Wallet.objects.create(tenant=tenant, balance_available=Decimal("0.00"))
    withdrawal = WithdrawalRequest.objects.create(
        wallet=wallet,
        amount=Decimal("10.00"),
        pix_key="38113982884",
        pix_key_type="CPF",
        status=WithdrawalRequest.Status.PAID,
        asaas_transfer_id="tra-paid-1",
    )

    process_transfer_asaas_event(
        event="TRANSFER_DONE",
        payload=_transfer_payload(event="TRANSFER_DONE", transfer_id="tra-paid-1"),
    )

    withdrawal.refresh_from_db()
    assert withdrawal.status == WithdrawalRequest.Status.PAID


@pytest.mark.django_db
def test_transfer_failed_refunds_balance():
    tenant = TenantFactory()
    wallet = Wallet.objects.create(
        tenant=tenant,
        balance_available=Decimal("0.00"),
    )
    withdrawal = WithdrawalRequest.objects.create(
        wallet=wallet,
        amount=Decimal("16.03"),
        pix_key="38113982884",
        pix_key_type="CPF",
        status=WithdrawalRequest.Status.PROCESSING,
        asaas_transfer_id="tra-fail-1",
    )

    process_transfer_asaas_event(
        event="TRANSFER_FAILED",
        payload=_transfer_payload(
            event="TRANSFER_FAILED",
            transfer_id="tra-fail-1",
            status="FAILED",
        ),
    )

    withdrawal.refresh_from_db()
    assert withdrawal.status == WithdrawalRequest.Status.REJECTED
    assert Wallet.objects.get(pk=wallet.pk).balance_available == Decimal("16.03")


@pytest.mark.django_db
def test_webhook_processor_routes_transfer_before_subscription():
    tenant = TenantFactory()
    wallet = Wallet.objects.create(tenant=tenant, balance_available=Decimal("0.00"))
    WithdrawalRequest.objects.create(
        wallet=wallet,
        amount=Decimal("16.03"),
        pix_key="38113982884",
        pix_key_type="CPF",
        status=WithdrawalRequest.Status.PROCESSING,
        asaas_transfer_id="591483b2-7ea8-45ec-a688-6eaf1fd068ac",
    )

    with mock.patch(
        "apps.billing.services.webhook_processor._process_subscription_webhook",
    ) as mock_sub:
        process_asaas_webhook_payload(
            _transfer_payload(
                event="TRANSFER_DONE",
                transfer_id="591483b2-7ea8-45ec-a688-6eaf1fd068ac",
            ),
        )

    mock_sub.assert_not_called()
    assert (
        WithdrawalRequest.objects.get(asaas_transfer_id="591483b2-7ea8-45ec-a688-6eaf1fd068ac").status
        == WithdrawalRequest.Status.PAID
    )


@pytest.mark.django_db
def test_webhook_http_post_transfer_done(settings, api_client: APIClient):
    settings.ASAAS_WEBHOOK_VERIFY = False
    tenant = TenantFactory()
    wallet = Wallet.objects.create(tenant=tenant, balance_available=Decimal("0.00"))
    WithdrawalRequest.objects.create(
        wallet=wallet,
        amount=Decimal("16.03"),
        pix_key="38113982884",
        pix_key_type="CPF",
        status=WithdrawalRequest.Status.PROCESSING,
        asaas_transfer_id="591483b2-7ea8-45ec-a688-6eaf1fd068ac",
    )

    resp = api_client.post(
        reverse("asaas-webhook"),
        _transfer_payload(
            event="TRANSFER_DONE",
            transfer_id="591483b2-7ea8-45ec-a688-6eaf1fd068ac",
        ),
        format="json",
    )

    assert resp.status_code == 200
    assert (
        WithdrawalRequest.objects.get(asaas_transfer_id="591483b2-7ea8-45ec-a688-6eaf1fd068ac").status
        == WithdrawalRequest.Status.PAID
    )

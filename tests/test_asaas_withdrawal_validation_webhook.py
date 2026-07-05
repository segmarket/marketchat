from decimal import Decimal

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from apps.financial.models import LedgerTransaction, Wallet, WithdrawalRequest
from tests.factories import TenantFactory

VALIDATION_URL = reverse("asaas-withdrawal-validation")
WITHDRAWAL_TOKEN = "test-withdrawal-token"


def _validation_payload(
    *,
    transfer_id: str,
    value: float = 40.0,
    external_reference: str = "marketchat-withdraw-abc123",
    description: str = "Saque MarketChat",
) -> dict:
    return {
        "type": "TRANSFER",
        "transfer": {
            "object": "transfer",
            "id": transfer_id,
            "status": "PENDING",
            "value": value,
            "netValue": value,
            "operationType": "PIX",
            "description": description,
            "externalReference": external_reference,
        },
    }


def _create_withdrawal(
    *,
    transfer_id: str,
    amount: Decimal = Decimal("40.00"),
) -> WithdrawalRequest:
    tenant = TenantFactory()
    wallet = Wallet.objects.create(
        tenant=tenant,
        balance_available=Decimal("0.00"),
        default_pix_key="11144477735",
        default_pix_key_type="CPF",
    )
    ledger = LedgerTransaction.objects.create(
        wallet=wallet,
        amount=amount,
        entry_type=LedgerTransaction.EntryType.OUTFLOW,
        description="Saque Pix",
        external_id=transfer_id,
    )
    return WithdrawalRequest.objects.create(
        wallet=wallet,
        amount=amount,
        pix_key="11144477735",
        pix_key_type="CPF",
        status=WithdrawalRequest.Status.PROCESSING,
        asaas_transfer_id=transfer_id,
        ledger_transaction=ledger,
    )


@pytest.mark.django_db
def test_withdrawal_validation_rejects_invalid_token(settings, api_client: APIClient):
    settings.ASAAS_WITHDRAWAL_TOKEN = WITHDRAWAL_TOKEN

    response = api_client.post(
        VALIDATION_URL,
        _validation_payload(transfer_id="tra_invalid"),
        format="json",
        HTTP_ASAAS_ACCESS_TOKEN="wrong-token",
    )

    assert response.status_code == 403


@pytest.mark.django_db
def test_withdrawal_validation_rejects_missing_token(settings, api_client: APIClient):
    settings.ASAAS_WITHDRAWAL_TOKEN = WITHDRAWAL_TOKEN

    response = api_client.post(
        VALIDATION_URL,
        _validation_payload(transfer_id="tra_invalid"),
        format="json",
    )

    assert response.status_code == 403


@pytest.mark.django_db
def test_withdrawal_validation_approves_known_transfer(settings, api_client: APIClient):
    settings.ASAAS_WITHDRAWAL_TOKEN = WITHDRAWAL_TOKEN
    transfer_id = "0bed986c-737d-49bf-a1cc-beca916797c4"
    _create_withdrawal(transfer_id=transfer_id, amount=Decimal("40.00"))

    response = api_client.post(
        VALIDATION_URL,
        _validation_payload(transfer_id=transfer_id, value=40.0),
        format="json",
        HTTP_ASAAS_ACCESS_TOKEN=WITHDRAWAL_TOKEN,
    )

    assert response.status_code == 200
    assert response.json() == {"status": "APPROVED"}


@pytest.mark.django_db
def test_withdrawal_validation_refuses_unknown_transfer(settings, api_client: APIClient):
    settings.ASAAS_WITHDRAWAL_TOKEN = WITHDRAWAL_TOKEN

    response = api_client.post(
        VALIDATION_URL,
        _validation_payload(transfer_id="tra_unknown_123"),
        format="json",
        HTTP_ASAAS_ACCESS_TOKEN=WITHDRAWAL_TOKEN,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "REFUSED"
    assert "refuseReason" in body


@pytest.mark.django_db
def test_withdrawal_validation_refuses_amount_mismatch(settings, api_client: APIClient):
    settings.ASAAS_WITHDRAWAL_TOKEN = WITHDRAWAL_TOKEN
    transfer_id = "591483b2-7ea8-45ec-a688-6eaf1fd068ac"
    _create_withdrawal(transfer_id=transfer_id, amount=Decimal("40.00"))

    response = api_client.post(
        VALIDATION_URL,
        _validation_payload(transfer_id=transfer_id, value=99.99),
        format="json",
        HTTP_ASAAS_ACCESS_TOKEN=WITHDRAWAL_TOKEN,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "REFUSED"
    assert "valor" in body["refuseReason"].lower()

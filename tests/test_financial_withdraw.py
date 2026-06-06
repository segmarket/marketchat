from decimal import Decimal
from unittest import mock

import pytest

from apps.financial.models import Wallet, WithdrawalRequest
from apps.financial.services.wallet import InsufficientBalanceError, request_withdrawal


@pytest.mark.django_db
def test_request_withdrawal_rejects_insufficient_balance():
    from tests.factories import TenantFactory

    tenant = TenantFactory()
    Wallet.objects.create(
        tenant=tenant,
        balance_available=Decimal("10.00"),
        default_pix_key="mercado@example.com",
        default_pix_key_type="EMAIL",
    )

    with pytest.raises(InsufficientBalanceError):
        request_withdrawal(tenant_id=tenant.id, amount=Decimal("20.00"))


@pytest.mark.django_db
@mock.patch("apps.financial.services.wallet.process_asaas_pix_transfer")
def test_request_withdrawal_debits_on_asaas_success(mock_transfer):
    from tests.factories import TenantFactory

    tenant = TenantFactory()
    Wallet.objects.create(
        tenant=tenant,
        balance_available=Decimal("100.00"),
        default_pix_key="mercado@example.com",
        default_pix_key_type="EMAIL",
    )
    mock_transfer.return_value = {"id": "tra_ok_1", "status": "DONE"}

    withdrawal = request_withdrawal(tenant_id=tenant.id, amount=Decimal("40.00"))

    wallet = Wallet.objects.get(tenant=tenant)
    assert wallet.balance_available == Decimal("60.00")
    assert wallet.balance_blocked == Decimal("0")
    assert withdrawal.status == WithdrawalRequest.Status.PAID
    assert withdrawal.asaas_transfer_id == "tra_ok_1"


@pytest.mark.django_db
@mock.patch("apps.financial.services.wallet.process_asaas_pix_transfer")
def test_request_withdrawal_processing_status(mock_transfer):
    from tests.factories import TenantFactory

    tenant = TenantFactory()
    Wallet.objects.create(
        tenant=tenant,
        balance_available=Decimal("50.00"),
        default_pix_key="11999990000",
        default_pix_key_type="PHONE",
    )
    mock_transfer.return_value = {"id": "tra_pending", "status": "PENDING"}

    withdrawal = request_withdrawal(tenant_id=tenant.id, amount=Decimal("10.00"))

    assert withdrawal.status == WithdrawalRequest.Status.PROCESSING
    assert Wallet.objects.get(tenant=tenant).balance_available == Decimal("40.00")


@pytest.mark.django_db
@mock.patch("apps.financial.services.wallet.process_asaas_pix_transfer")
def test_request_withdrawal_does_not_debit_on_asaas_failure(mock_transfer):
    from apps.financial.services.asaas_transfers import AsaasTransferError
    from tests.factories import TenantFactory

    tenant = TenantFactory()
    Wallet.objects.create(
        tenant=tenant,
        balance_available=Decimal("80.00"),
        default_pix_key="mercado@example.com",
        default_pix_key_type="EMAIL",
    )
    mock_transfer.side_effect = AsaasTransferError("Saldo insuficiente na conta Asaas.")

    with pytest.raises(AsaasTransferError):
        request_withdrawal(tenant_id=tenant.id, amount=Decimal("30.00"))

    wallet = Wallet.objects.get(tenant=tenant)
    assert wallet.balance_available == Decimal("80.00")
    assert WithdrawalRequest.objects.count() == 0

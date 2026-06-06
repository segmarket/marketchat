from decimal import Decimal
from unittest import mock

import pytest
from django.db import IntegrityError

from apps.financial.models import LedgerTransaction, Wallet
from apps.financial.services.wallet import (
    calculate_net_amount,
    credit_sale_payment,
    request_withdrawal,
)
from tests.factories import CartFactory, CartItemFactory, ProductFactory, ResidentFactory, TenantFactory


@pytest.mark.django_db
def test_calculate_net_amount_applies_two_percent_fee(settings):
    settings.FINANCIAL_PLATFORM_FEE_PERCENT = 2
    net, fee = calculate_net_amount(Decimal("100.00"))
    assert net == Decimal("98.00")
    assert fee == Decimal("2.00")


@pytest.mark.django_db
def test_credit_sale_payment_creates_wallet_and_ledger():
    tenant = TenantFactory()
    resident = ResidentFactory(tenant=tenant)
    product = ProductFactory(tenant=tenant, name="Coca-Cola Zero")
    cart = CartFactory(tenant=tenant, resident=resident, total_value=Decimal("50.00"))
    CartItemFactory(cart=cart, product=product, quantity=2, unit_price=Decimal("25.00"))

    ledger = credit_sale_payment(cart, payment_id="pay_test_1", gross_amount=Decimal("50.00"))

    assert ledger is not None
    wallet = Wallet.objects.get(tenant=tenant)
    assert wallet.balance_available == Decimal("49.00")
    assert ledger.entry_type == LedgerTransaction.EntryType.INFLOW
    assert ledger.external_id == "pay_test_1"
    assert "Coca-Cola Zero" in ledger.description
    assert "taxa 2%" in ledger.description


@pytest.mark.django_db
def test_credit_sale_payment_is_idempotent():
    tenant = TenantFactory()
    resident = ResidentFactory(tenant=tenant)
    cart = CartFactory(tenant=tenant, resident=resident, total_value=Decimal("10.00"))

    first = credit_sale_payment(cart, payment_id="pay_dup", gross_amount=Decimal("10.00"))
    second = credit_sale_payment(cart, payment_id="pay_dup", gross_amount=Decimal("10.00"))

    assert first is not None
    assert second is None
    wallet = Wallet.objects.get(tenant=tenant)
    assert wallet.balance_available == Decimal("9.80")
    assert LedgerTransaction.objects.filter(external_id="pay_dup").count() == 1


@pytest.mark.django_db
def test_credit_sale_payment_unique_constraint():
    tenant = TenantFactory()
    wallet = Wallet.objects.create(tenant=tenant)
    LedgerTransaction.objects.create(
        wallet=wallet,
        amount=Decimal("1.00"),
        entry_type=LedgerTransaction.EntryType.INFLOW,
        description="existing",
        external_id="pay_unique",
    )

    with pytest.raises(IntegrityError):
        LedgerTransaction.objects.create(
            wallet=wallet,
            amount=Decimal("2.00"),
            entry_type=LedgerTransaction.EntryType.INFLOW,
            description="duplicate",
            external_id="pay_unique",
        )


@pytest.mark.django_db
@mock.patch("apps.financial.services.wallet.process_asaas_pix_transfer")
def test_request_withdrawal_debits_available_on_success(mock_transfer):
    tenant = TenantFactory()
    wallet = Wallet.objects.create(
        tenant=tenant,
        balance_available=Decimal("100.00"),
        default_pix_key="11999990000",
        default_pix_key_type="PHONE",
    )
    mock_transfer.return_value = {"id": "tra_wallet_1", "status": "DONE"}

    withdrawal = request_withdrawal(tenant_id=tenant.id, amount=Decimal("40.00"))

    wallet.refresh_from_db()
    assert wallet.balance_available == Decimal("60.00")
    assert wallet.balance_blocked == Decimal("0")
    assert withdrawal.status == withdrawal.Status.PAID
    assert withdrawal.ledger_transaction is not None
    assert withdrawal.ledger_transaction.entry_type == LedgerTransaction.EntryType.OUTFLOW

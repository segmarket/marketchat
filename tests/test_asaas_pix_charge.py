from decimal import Decimal
from unittest import mock

import pytest

from apps.billing.models import AsaasSubaccount
from apps.billing.services.asaas_pix_charge import (
    create_cart_pix_charge,
    extract_pix_copy_paste,
    fetch_pix_copy_paste,
    use_main_account_pix_dev,
)
from tests.factories import (
    AsaasSubaccountFactory,
    CartFactory,
    ResidentFactory,
    TenantFactory,
)


def test_extract_pix_copy_paste_from_qrcode_endpoint():
    payload = {"payload": "00020126580014br.gov.bcb.pix"}
    assert extract_pix_copy_paste(payload) == "00020126580014br.gov.bcb.pix"


@pytest.mark.django_db
def test_fetch_pix_copy_paste_calls_asaas_endpoint():
    client = mock.Mock()
    client.get_payment_pix_qrcode.return_value = {"payload": "pix-code-123"}
    assert fetch_pix_copy_paste(client, "pay_abc") == "pix-code-123"
    client.get_payment_pix_qrcode.assert_called_once_with("pay_abc")


@pytest.mark.django_db
def test_create_cart_pix_fetches_qrcode_when_missing_on_create():
    tenant = TenantFactory()
    AsaasSubaccountFactory(
        tenant=tenant,
        account_status=AsaasSubaccount.AccountStatus.APPROVED,
    )
    resident = ResidentFactory(tenant=tenant)
    cart = CartFactory(tenant=tenant, resident=resident, total_value=Decimal("25.00"))

    client = mock.Mock()
    client.create_payment.return_value = {"id": "pay_xyz", "status": "PENDING"}
    client.get_payment_pix_qrcode.return_value = {"payload": "000201PIX"}

    with mock.patch(
        "apps.billing.services.asaas_pix_charge.get_or_create_resident_customer",
        return_value="cus_test",
    ):
        with mock.patch(
            "apps.billing.services.asaas_pix_charge.AsaasClient",
            return_value=client,
        ):
            code = create_cart_pix_charge(cart, resident)

    assert code == "000201PIX"
    client.get_payment_pix_qrcode.assert_called_once_with("pay_xyz")


@pytest.mark.django_db
def test_dev_main_account_skips_split_and_pending_check(settings):
    settings.DEBUG = True
    settings.ASAAS_PIX_USE_MAIN_ACCOUNT_IN_DEV = True

    tenant = TenantFactory()
    AsaasSubaccountFactory(
        tenant=tenant,
        account_status=AsaasSubaccount.AccountStatus.PENDING,
    )
    resident = ResidentFactory(tenant=tenant)
    cart = CartFactory(tenant=tenant, resident=resident, total_value=Decimal("12.00"))

    client = mock.Mock()
    client.create_payment.return_value = {"id": "pay_dev"}
    client.get_payment_pix_qrcode.return_value = {"payload": "pix-dev-main"}

    with mock.patch(
        "apps.billing.services.asaas_pix_charge.get_or_create_resident_customer",
        return_value="cus_dev",
    ):
        with mock.patch(
            "apps.billing.services.asaas_pix_charge.AsaasClient",
            return_value=client,
        ):
            code = create_cart_pix_charge(cart, resident)

    assert code == "pix-dev-main"
    body = client.create_payment.call_args[0][0]
    assert "split" not in body
    assert use_main_account_pix_dev() is True


@pytest.mark.django_db
def test_create_cart_pix_rejects_pending_subaccount(settings):
    settings.DEBUG = False
    settings.ASAAS_PIX_USE_MAIN_ACCOUNT_IN_DEV = False
    tenant = TenantFactory()
    AsaasSubaccountFactory(
        tenant=tenant,
        account_status=AsaasSubaccount.AccountStatus.PENDING,
    )
    resident = ResidentFactory(tenant=tenant)
    cart = CartFactory(tenant=tenant, resident=resident, total_value=Decimal("10.00"))

    from apps.billing.services.asaas_pix_charge import PixChargeError

    with pytest.raises(PixChargeError, match="em análise"):
        create_cart_pix_charge(cart, resident)

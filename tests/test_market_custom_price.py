from decimal import Decimal
from unittest import mock

import pytest
from django.contrib.admin.sites import AdminSite
from django.contrib.auth.models import Group
from django.test import RequestFactory

from apps.billing.services.subscription_sync import update_tenant_subscription_value
from apps.markets.admin import MarketAdmin
from apps.markets.models import Market
from tests.factories import MarketFactory, SubscriptionFactory, TenantFactory


@pytest.mark.django_db
def test_computed_subscription_value_mixes_custom_and_default(settings):
    settings.MARKET_MONTHLY_PRICE = 59.90
    tenant = TenantFactory()
    MarketFactory(tenant=tenant, status=Market.Status.ACTIVE, custom_price=None)
    MarketFactory(
        tenant=tenant,
        status=Market.Status.ACTIVE,
        custom_price=Decimal("39.90"),
    )
    MarketFactory(
        tenant=tenant,
        status=Market.Status.INACTIVE,
        custom_price=Decimal("10.00"),
    )

    assert tenant.computed_subscription_value() == round(59.90 + 39.90, 2)


@pytest.mark.django_db
def test_computed_subscription_value_all_custom(settings):
    settings.MARKET_MONTHLY_PRICE = 59.90
    tenant = TenantFactory()
    MarketFactory(tenant=tenant, custom_price=Decimal("20.00"))
    MarketFactory(tenant=tenant, custom_price=Decimal("30.50"))
    assert tenant.computed_subscription_value() == 50.50


@pytest.mark.django_db
@mock.patch("apps.markets.admin.messages.info")
@mock.patch("apps.markets.admin.transaction.on_commit", side_effect=lambda fn: fn())
@mock.patch("apps.markets.admin.update_tenant_subscription_value")
def test_market_admin_save_schedules_subscription_sync(mock_sync, _on_commit, _msg):
    tenant = TenantFactory()
    SubscriptionFactory(tenant=tenant)
    admin_obj = MarketAdmin(Market, AdminSite())
    request = RequestFactory().post("/admin/markets/market/add/")

    market = Market(
        tenant=tenant,
        name="Novo Mercado",
        address="Rua 1",
        status=Market.Status.ACTIVE,
        custom_price=Decimal("45.00"),
    )
    admin_obj.save_model(request, market, form=None, change=False)

    market.refresh_from_db()
    assert market.custom_price == Decimal("45.00")
    mock_sync.assert_called_once()
    synced_tenant = mock_sync.call_args[0][0]
    assert synced_tenant.pk == tenant.pk


@pytest.mark.django_db
@mock.patch("apps.billing.services.subscription_sync.AsaasClient")
def test_update_tenant_subscription_value_uses_custom_sum(mock_client_cls, settings):
    settings.MARKET_MONTHLY_PRICE = 59.90
    tenant = TenantFactory()
    sub = SubscriptionFactory(tenant=tenant)
    MarketFactory(tenant=tenant, custom_price=Decimal("40.00"))
    MarketFactory(tenant=tenant, custom_price=None)

    client = mock_client_cls.return_value
    update_tenant_subscription_value(tenant)

    client.update_subscription.assert_called_once_with(
        sub.asaas_subscription_id,
        {
            "value": round(40.0 + 59.90, 2),
            "status": "ACTIVE",
            "updatePendingPayments": True,
        },
    )


@pytest.mark.django_db
def test_sellers_group_permissions():
    group = Group.objects.filter(name="Vendedores").first()
    assert group is not None
    codenames = set(group.permissions.values_list("codename", flat=True))
    assert "add_market" in codenames
    assert "change_market" in codenames
    assert "view_market" in codenames
    assert "view_tenant" in codenames
    assert "delete_market" not in codenames

from unittest import mock

import pytest
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.billing.models import Subscription
from apps.markets.models import Market
from apps.tenants.models import Tenant
from tests.factories import MarketFactory, SubscriptionFactory, TenantFactory, UserFactory


def _auth_client(user) -> APIClient:
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(user).access_token}")
    return client


@pytest.mark.django_db
def test_reactivate_subscription_success():
    tenant = TenantFactory(subscription_status=Tenant.SubscriptionStatus.CANCELED)
    sub = SubscriptionFactory(
        tenant=tenant,
        status=Subscription.Status.CANCELLED,
        asaas_subscription_id="sub_old",
    )
    MarketFactory(tenant=tenant, status=Market.Status.ACTIVE)
    user = UserFactory(tenant=tenant, is_tenant_admin=True)
    client = _auth_client(user)

    summary = {
        "subscription_status": "ACTIVE",
        "can_reactivate": False,
        "billing_type": "CREDIT_CARD",
        "display_label": "Visa terminando em 4242",
    }

    with (
        mock.patch("apps.billing.services.subscription_reactivate.AsaasClient") as mock_cls,
        mock.patch(
            "apps.billing.views_settings.get_payment_method_summary",
            return_value=summary,
        ),
    ):
        inst = mock_cls.return_value
        inst.get_subscription.return_value = {"status": "INACTIVE", "id": "sub_old"}
        inst.update_subscription.return_value = {"id": "sub_old", "status": "ACTIVE"}
        response = client.post(reverse("settings-billing-reactivate-subscription"))

    assert response.status_code == 200
    tenant.refresh_from_db()
    sub.refresh_from_db()
    assert tenant.subscription_status == Tenant.SubscriptionStatus.ACTIVE
    assert sub.status == Subscription.Status.ACTIVE
    assert tenant.overdue_since is None
    assert response.json().get("can_reactivate") is False


@pytest.mark.django_db
def test_reactivate_creates_new_subscription_when_old_missing():
    tenant = TenantFactory(subscription_status=Tenant.SubscriptionStatus.CANCELED)
    sub = SubscriptionFactory(
        tenant=tenant,
        status=Subscription.Status.CANCELLED,
        asaas_subscription_id="sub_deleted",
        asaas_customer_id="cus_123",
    )
    MarketFactory(tenant=tenant, status=Market.Status.ACTIVE)
    user = UserFactory(tenant=tenant, is_tenant_admin=True)
    client = _auth_client(user)

    from apps.billing.services.asaas_client import AsaasAPIError

    summary = {
        "subscription_status": "ACTIVE",
        "can_reactivate": False,
        "billing_type": "CREDIT_CARD",
        "display_label": "Cartão",
    }

    with (
        mock.patch("apps.billing.services.subscription_reactivate.AsaasClient") as mock_cls,
        mock.patch(
            "apps.billing.views_settings.get_payment_method_summary",
            return_value=summary,
        ),
    ):
        inst = mock_cls.return_value
        inst.get_subscription.side_effect = AsaasAPIError("not found", status_code=404)
        inst.create_subscription.return_value = {"id": "sub_new", "status": "ACTIVE"}

        response = client.post(reverse("settings-billing-reactivate-subscription"))

    assert response.status_code == 200
    sub.refresh_from_db()
    assert sub.asaas_subscription_id == "sub_new"
    tenant.refresh_from_db()
    assert tenant.subscription_status == Tenant.SubscriptionStatus.ACTIVE


@pytest.mark.django_db
def test_reactivate_requires_active_markets():
    tenant = TenantFactory(subscription_status=Tenant.SubscriptionStatus.CANCELED)
    SubscriptionFactory(tenant=tenant, status=Subscription.Status.CANCELLED)
    user = UserFactory(tenant=tenant, is_tenant_admin=True)
    client = _auth_client(user)

    response = client.post(reverse("settings-billing-reactivate-subscription"))

    assert response.status_code == 400
    assert "mercado" in response.json()["detail"].lower()


@pytest.mark.django_db
def test_reactivate_conflict_when_not_canceled():
    tenant = TenantFactory(subscription_status=Tenant.SubscriptionStatus.ACTIVE)
    SubscriptionFactory(tenant=tenant, status=Subscription.Status.ACTIVE)
    user = UserFactory(tenant=tenant, is_tenant_admin=True)
    client = _auth_client(user)

    response = client.post(reverse("settings-billing-reactivate-subscription"))

    assert response.status_code == 409


@pytest.mark.django_db
def test_reactivate_non_admin_forbidden():
    tenant = TenantFactory(subscription_status=Tenant.SubscriptionStatus.CANCELED)
    SubscriptionFactory(tenant=tenant, status=Subscription.Status.CANCELLED)
    MarketFactory(tenant=tenant)
    user = UserFactory(tenant=tenant, is_tenant_admin=False)
    client = _auth_client(user)

    response = client.post(reverse("settings-billing-reactivate-subscription"))

    assert response.status_code == 403


@pytest.mark.django_db
def test_reactivate_card_error_returns_402():
    tenant = TenantFactory(subscription_status=Tenant.SubscriptionStatus.CANCELED)
    SubscriptionFactory(
        tenant=tenant,
        status=Subscription.Status.CANCELLED,
        asaas_customer_id="cus_1",
    )
    MarketFactory(tenant=tenant)
    user = UserFactory(tenant=tenant, is_tenant_admin=True)
    client = _auth_client(user)

    from apps.billing.services.subscription_reactivate import ReactivationCardError

    with mock.patch(
        "apps.billing.views_settings.reactivate_tenant_subscription",
        side_effect=ReactivationCardError("card"),
    ):
        response = client.post(reverse("settings-billing-reactivate-subscription"))

    assert response.status_code == 402
    assert response.json().get("code") == "card_required"

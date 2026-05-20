from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.billing.models import Subscription
from apps.tenants.models import Tenant
from tests.factories import SubscriptionFactory, TenantFactory, UserFactory


def _auth_client(user) -> APIClient:
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(user).access_token}")
    return client


@pytest.mark.django_db
def test_expired_trial_without_subscription_returns_402_trial_expired():
    tenant = TenantFactory(
        trial_started_at=timezone.now() - timedelta(days=8),
        trial_ends_at=timezone.now() - timedelta(days=1),
        subscription_status=Tenant.SubscriptionStatus.TRIAL,
    )
    user = UserFactory(tenant=tenant)
    client = _auth_client(user)

    response = client.get(reverse("products-list"))

    assert response.status_code == 402
    assert response.json()["error"] == "trial_expired"


@pytest.mark.django_db
def test_active_trial_allows_panel_api():
    tenant = TenantFactory(
        trial_started_at=timezone.now(),
        trial_ends_at=timezone.now() + timedelta(days=5),
        subscription_status=Tenant.SubscriptionStatus.TRIAL,
    )
    user = UserFactory(tenant=tenant)
    client = _auth_client(user)

    response = client.get(reverse("products-list"))

    assert response.status_code == 200


@pytest.mark.django_db
def test_me_returns_days_left_in_trial():
    tenant = TenantFactory(
        trial_started_at=timezone.now(),
        trial_ends_at=timezone.now() + timedelta(days=5),
        subscription_status=Tenant.SubscriptionStatus.TRIAL,
    )
    user = UserFactory(tenant=tenant)
    client = _auth_client(user)

    response = client.get(reverse("auth-me"))

    assert response.status_code == 200
    data = response.json()
    assert data["subscription_status"] == Tenant.SubscriptionStatus.TRIAL
    assert 1 <= data["days_left_in_trial"] <= 7
    assert data["trial_expired"] is False
    assert data["billing_blocked"] is False


@pytest.mark.django_db
def test_expired_trial_with_active_subscription_allows_access():
    tenant = TenantFactory(
        trial_started_at=timezone.now() - timedelta(days=10),
        trial_ends_at=timezone.now() - timedelta(days=3),
        subscription_status=Tenant.SubscriptionStatus.TRIAL,
    )
    SubscriptionFactory(tenant=tenant, status=Subscription.Status.ACTIVE)
    user = UserFactory(tenant=tenant)
    client = _auth_client(user)

    response = client.get(reverse("products-list"))

    assert response.status_code == 200


@pytest.mark.django_db
def test_billing_blocked_returns_402_billing_suspended():
    tenant = TenantFactory(
        trial_started_at=timezone.now(),
        trial_ends_at=timezone.now() + timedelta(days=7),
        subscription_status=Tenant.SubscriptionStatus.SUSPENDED,
        billing_blocked_at=timezone.now(),
    )
    user = UserFactory(tenant=tenant)
    client = _auth_client(user)

    response = client.get(reverse("products-list"))

    assert response.status_code == 402
    assert response.json()["error"] == "billing_suspended"


@pytest.mark.django_db
def test_settings_billing_bypasses_panel_block():
    tenant = TenantFactory(
        trial_started_at=timezone.now() - timedelta(days=8),
        trial_ends_at=timezone.now() - timedelta(days=1),
        subscription_status=Tenant.SubscriptionStatus.TRIAL,
    )
    user = UserFactory(tenant=tenant, is_tenant_admin=True)
    client = _auth_client(user)

    response = client.get(reverse("settings-billing-payment-method"))

    assert response.status_code in (200, 404, 502)

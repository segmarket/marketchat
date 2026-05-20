from datetime import timedelta
from unittest import mock

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
def test_cancel_subscription_during_trial_keeps_panel_access():
    tenant = TenantFactory(
        trial_started_at=timezone.now(),
        trial_ends_at=timezone.now() + timedelta(days=5),
        subscription_status=Tenant.SubscriptionStatus.TRIAL,
    )
    sub = SubscriptionFactory(tenant=tenant, status=Subscription.Status.ACTIVE)
    user = UserFactory(tenant=tenant, is_tenant_admin=True)
    client = _auth_client(user)

    with mock.patch("apps.billing.services.subscription_cancel.AsaasClient") as mock_cls:
        inst = mock_cls.return_value
        inst.cancel_subscription.return_value = {"deleted": True, "id": sub.asaas_subscription_id}
        response = client.post(reverse("settings-billing-cancel-subscription"))

    assert response.status_code == 200
    tenant.refresh_from_db()
    sub.refresh_from_db()
    assert tenant.subscription_status == Tenant.SubscriptionStatus.CANCELED
    assert sub.status == Subscription.Status.CANCELLED
    assert tenant.billing_blocked_at is None

    panel = client.get(reverse("products-list"))
    assert panel.status_code == 200


@pytest.mark.django_db
def test_cancel_subscription_after_trial_blocks_panel():
    tenant = TenantFactory(
        trial_started_at=timezone.now() - timedelta(days=10),
        trial_ends_at=timezone.now() - timedelta(days=3),
        subscription_status=Tenant.SubscriptionStatus.ACTIVE,
    )
    sub = SubscriptionFactory(tenant=tenant, status=Subscription.Status.ACTIVE)
    user = UserFactory(tenant=tenant, is_tenant_admin=True)
    client = _auth_client(user)

    with mock.patch("apps.billing.services.subscription_cancel.AsaasClient") as mock_cls:
        inst = mock_cls.return_value
        inst.cancel_subscription.return_value = {"deleted": True, "id": sub.asaas_subscription_id}
        response = client.post(reverse("settings-billing-cancel-subscription"))

    assert response.status_code == 200
    tenant.refresh_from_db()
    assert tenant.billing_blocked_at is not None

    panel = client.get(reverse("products-list"))
    assert panel.status_code == 402


@pytest.mark.django_db
def test_cancel_subscription_idempotent_error():
    tenant = TenantFactory(subscription_status=Tenant.SubscriptionStatus.CANCELED)
    SubscriptionFactory(tenant=tenant, status=Subscription.Status.CANCELLED)
    user = UserFactory(tenant=tenant, is_tenant_admin=True)
    client = _auth_client(user)

    response = client.post(reverse("settings-billing-cancel-subscription"))

    assert response.status_code == 400

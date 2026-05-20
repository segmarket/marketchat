from datetime import timedelta
from unittest import mock

import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.billing.models import Subscription
from apps.billing.services.webhook_processor import process_asaas_webhook_payload
from apps.markets.models import Market
from apps.tenants.models import Tenant
from tests.factories import SubscriptionFactory, TenantFactory, UserFactory


def _auth_client(user) -> APIClient:
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(user).access_token}")
    return client


@pytest.mark.django_db
def test_grace_period_allows_panel_access_day_2():
    tenant = TenantFactory(
        trial_started_at=timezone.now() - timedelta(days=30),
        trial_ends_at=timezone.now() - timedelta(days=20),
        subscription_status=Tenant.SubscriptionStatus.OVERDUE,
        overdue_since=timezone.now() - timedelta(days=2),
    )
    SubscriptionFactory(tenant=tenant, status=Subscription.Status.OVERDUE)
    user = UserFactory(tenant=tenant)
    client = _auth_client(user)

    response = client.get(reverse("products-list"))
    assert response.status_code == 200

    me = client.get(reverse("auth-me"))
    assert me.status_code == 200
    assert me.json()["is_in_grace_period"] is True


@pytest.mark.django_db
def test_overdue_day_4_blocks_and_suspends():
    tenant = TenantFactory(
        trial_started_at=timezone.now() - timedelta(days=30),
        trial_ends_at=timezone.now() - timedelta(days=20),
        subscription_status=Tenant.SubscriptionStatus.OVERDUE,
        overdue_since=timezone.now() - timedelta(days=4),
    )
    SubscriptionFactory(tenant=tenant, status=Subscription.Status.OVERDUE)
    user = UserFactory(tenant=tenant)
    client = _auth_client(user)

    with mock.patch(
        "apps.billing.services.tenant_suspension.disconnect_whatsapp_instance",
    ):
        response = client.get(reverse("products-list"))

    assert response.status_code == 402
    assert response.json()["error"] == "billing_suspended"
    tenant.refresh_from_db()
    assert tenant.subscription_status == Tenant.SubscriptionStatus.SUSPENDED


@pytest.mark.django_db
def test_payment_overdue_webhook_sets_overdue_without_block():
    tenant = TenantFactory(
        subscription_status=Tenant.SubscriptionStatus.ACTIVE,
    )
    sub = SubscriptionFactory(tenant=tenant, status=Subscription.Status.ACTIVE)

    process_asaas_webhook_payload(
        {
            "event": "PAYMENT_OVERDUE",
            "payment": {"subscription": sub.asaas_subscription_id},
        },
    )

    tenant.refresh_from_db()
    assert tenant.subscription_status == Tenant.SubscriptionStatus.OVERDUE
    assert tenant.overdue_since is not None
    assert tenant.billing_blocked_at is None


@pytest.mark.django_db
def test_payment_received_clears_overdue():
    tenant = TenantFactory(
        subscription_status=Tenant.SubscriptionStatus.OVERDUE,
        overdue_since=timezone.now() - timedelta(days=2),
        billing_blocked_at=timezone.now(),
    )
    sub = SubscriptionFactory(tenant=tenant, status=Subscription.Status.OVERDUE)

    process_asaas_webhook_payload(
        {
            "event": "PAYMENT_RECEIVED",
            "payment": {"subscription": sub.asaas_subscription_id},
        },
    )

    tenant.refresh_from_db()
    assert tenant.subscription_status == Tenant.SubscriptionStatus.ACTIVE
    assert tenant.overdue_since is None
    assert tenant.billing_blocked_at is None


@pytest.mark.django_db
def test_market_create_syncs_subscription_value():
    tenant = TenantFactory()
    sub = SubscriptionFactory(tenant=tenant)
    user = UserFactory(tenant=tenant)
    client = _auth_client(user)

    with (
        mock.patch("apps.markets.views.transaction.on_commit", lambda fn: fn()),
        mock.patch("apps.billing.services.subscription_sync.AsaasClient") as mock_cls,
    ):
        inst = mock_cls.return_value
        response = client.post(
            reverse("markets-list"),
            {"name": "Mercado 1", "address": "Rua A, 1", "status": "active"},
            format="json",
        )

    assert response.status_code == 201
    inst.update_subscription.assert_called_once()
    call_args = inst.update_subscription.call_args
    assert call_args[0][0] == sub.asaas_subscription_id
    assert call_args[0][1]["value"] == 59.90
    assert call_args[0][1]["status"] == "ACTIVE"


@pytest.mark.django_db
def test_zero_active_markets_pauses_subscription():
    tenant = TenantFactory()
    sub = SubscriptionFactory(tenant=tenant)
    Market.objects.create(
        tenant=tenant,
        name="Inativo",
        address="Rua B",
        status=Market.Status.INACTIVE,
    )

    with mock.patch(
        "apps.billing.services.subscription_sync.AsaasClient",
    ) as mock_cls:
        inst = mock_cls.return_value
        from apps.billing.services.subscription_sync import update_tenant_subscription_value

        update_tenant_subscription_value(tenant)

    inst.update_subscription.assert_called_once_with(
        sub.asaas_subscription_id,
        {"status": "INACTIVE"},
    )


@pytest.mark.django_db
def test_subscription_deleted_does_not_cancel_on_payment_failure():
    tenant = TenantFactory(
        subscription_status=Tenant.SubscriptionStatus.ACTIVE,
    )
    sub = SubscriptionFactory(tenant=tenant, status=Subscription.Status.ACTIVE)

    process_asaas_webhook_payload(
        {
            "event": "SUBSCRIPTION_DELETED",
            "subscription": {"id": sub.asaas_subscription_id},
        },
    )

    tenant.refresh_from_db()
    sub.refresh_from_db()
    assert tenant.subscription_status == Tenant.SubscriptionStatus.OVERDUE
    assert tenant.overdue_since is not None
    assert tenant.subscription_status != Tenant.SubscriptionStatus.CANCELED


@pytest.mark.django_db
def test_subscription_deleted_idempotent_when_already_canceled():
    tenant = TenantFactory(
        subscription_status=Tenant.SubscriptionStatus.CANCELED,
    )
    sub = SubscriptionFactory(tenant=tenant, status=Subscription.Status.CANCELLED)

    process_asaas_webhook_payload(
        {
            "event": "SUBSCRIPTION_DELETED",
            "subscription": {"id": sub.asaas_subscription_id},
        },
    )

    tenant.refresh_from_db()
    assert tenant.subscription_status == Tenant.SubscriptionStatus.CANCELED


@pytest.mark.django_db
def test_payment_rejected_sets_overdue():
    tenant = TenantFactory(
        subscription_status=Tenant.SubscriptionStatus.TRIAL,
        trial_started_at=timezone.now() - timedelta(days=10),
        trial_ends_at=timezone.now() - timedelta(days=1),
    )
    sub = SubscriptionFactory(tenant=tenant, status=Subscription.Status.ACTIVE)

    process_asaas_webhook_payload(
        {
            "event": "PAYMENT_REJECTED",
            "payment": {"subscription": sub.asaas_subscription_id},
        },
    )

    tenant.refresh_from_db()
    assert tenant.subscription_status == Tenant.SubscriptionStatus.OVERDUE
    assert tenant.overdue_since is not None

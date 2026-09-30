from __future__ import annotations

from datetime import timedelta
from unittest import mock

import pytest
from django.core import mail
from django.utils import timezone

from apps.billing.models import Subscription
from apps.billing.services.subscription_enforcement import (
    clear_tenant_operational_state,
    enforce_tenant_suspension,
    iter_tenants_pending_suspension,
    suspension_reason_for_tenant,
)
from apps.billing.services.tenant_suspension import tenant_has_messaging_access
from apps.core.emails import SUBSCRIPTION_SUSPENDED_SUBJECT
from apps.integrations.models import WhatsappInstance
from apps.residents.models import ChatSession
from apps.sales.models import Cart
from apps.tenants.models import Tenant
from tests.factories import (
    ResidentFactory,
    SubscriptionFactory,
    TenantFactory,
    UserFactory,
    WhatsappInstanceFactory,
)


@pytest.mark.django_db
def test_suspension_reason_trial_expired():
    tenant = TenantFactory(
        trial_ends_at=timezone.now() - timedelta(days=1),
        subscription_status=Tenant.SubscriptionStatus.TRIAL,
    )
    assert suspension_reason_for_tenant(tenant) == "trial_expired"


@pytest.mark.django_db
def test_suspension_reason_overdue_after_grace():
    tenant = TenantFactory(
        subscription_status=Tenant.SubscriptionStatus.OVERDUE,
        overdue_since=timezone.now() - timedelta(days=4),
    )
    assert suspension_reason_for_tenant(tenant) == "billing_overdue"


@pytest.mark.django_db
def test_iter_pending_suspension_excludes_grace_overdue():
    TenantFactory(
        subscription_status=Tenant.SubscriptionStatus.OVERDUE,
        overdue_since=timezone.now() - timedelta(days=1),
    )
    expired = TenantFactory(
        trial_ends_at=timezone.now() - timedelta(hours=1),
        subscription_status=Tenant.SubscriptionStatus.TRIAL,
    )
    pending = list(iter_tenants_pending_suspension())
    ids = {p.tenant.pk for p in pending}
    assert expired.pk in ids
    assert len(pending) == 1


@pytest.mark.django_db
def test_enforce_trial_suspends_and_sends_email():
    tenant = TenantFactory(
        trial_ends_at=timezone.now() - timedelta(days=1),
        subscription_status=Tenant.SubscriptionStatus.TRIAL,
    )
    SubscriptionFactory(tenant=tenant, status=Subscription.Status.ACTIVE)
    admin = UserFactory(tenant=tenant, is_tenant_admin=True, email="owner@suspend.test")
    WhatsappInstanceFactory(tenant=tenant, is_active=True, api_key="evo-key-test")

    mail.outbox.clear()
    with mock.patch(
        "apps.billing.services.subscription_enforcement.logout_whatsapp_session",
    ) as mock_logout:
        ok = enforce_tenant_suspension(tenant, reason="trial_expired", send_email=True)

    assert ok is True
    mock_logout.assert_called_once()
    tenant.refresh_from_db()
    assert tenant.subscription_status == Tenant.SubscriptionStatus.SUSPENDED
    assert tenant.billing_blocked_at is not None
    tenant.subscription.refresh_from_db()
    assert tenant.subscription.status == Subscription.Status.INACTIVE
    assert len(mail.outbox) == 1
    assert mail.outbox[0].subject == SUBSCRIPTION_SUSPENDED_SUBJECT
    assert "owner@suspend.test" in mail.outbox[0].to


@pytest.mark.django_db
def test_enforce_blocks_locally_even_when_evolution_logout_fails():
    tenant = TenantFactory(
        trial_ends_at=timezone.now() - timedelta(days=1),
        subscription_status=Tenant.SubscriptionStatus.TRIAL,
    )
    WhatsappInstanceFactory(tenant=tenant, is_active=True, api_key="evo-key-fail")

    with mock.patch(
        "apps.billing.services.subscription_enforcement.logout_whatsapp_session",
        side_effect=TimeoutError("evolution down"),
    ):
        ok = enforce_tenant_suspension(tenant, reason="trial_expired", send_email=True)

    assert ok is True
    tenant.refresh_from_db()
    assert tenant.subscription_status == Tenant.SubscriptionStatus.SUSPENDED
    assert tenant.billing_blocked_at is not None
    assert tenant.whatsapp_logout_pending_since is not None


@pytest.mark.django_db
def test_enforce_is_noop_when_tenant_no_longer_eligible():
    tenant = TenantFactory(
        trial_ends_at=timezone.now() - timedelta(days=1),
        subscription_status=Tenant.SubscriptionStatus.ACTIVE,
    )
    with mock.patch(
        "apps.billing.services.subscription_enforcement.logout_whatsapp_session",
    ) as logout:
        ok = enforce_tenant_suspension(tenant, reason="trial_expired", send_email=False)

    assert ok is False
    logout.assert_not_called()
    tenant.refresh_from_db()
    assert tenant.subscription_status == Tenant.SubscriptionStatus.ACTIVE


@pytest.mark.django_db
def test_clear_tenant_operational_state_cancels_carts_and_resets_sessions():
    tenant = TenantFactory()
    resident = ResidentFactory(tenant=tenant)
    cart = Cart.objects.create(
        tenant=tenant,
        resident=resident,
        status=Cart.Status.AWAITING_PAYMENT,
    )
    ChatSession.objects.create(
        tenant=tenant,
        phone_number=resident.phone_number,
        state=ChatSession.State.CART_REVIEW,
        active_cart=cart,
    )

    cancelled = clear_tenant_operational_state(tenant.pk)
    assert cancelled == 1
    cart.refresh_from_db()
    assert cart.status == Cart.Status.CANCELLED
    session = ChatSession.objects.get(tenant=tenant, phone_number=resident.phone_number)
    assert session.state == ChatSession.State.IDLE
    assert session.active_cart_id is None


@pytest.mark.django_db
def test_tenant_has_messaging_access_blocks_expired_trial():
    tenant = TenantFactory(
        trial_ends_at=timezone.now() - timedelta(days=1),
        subscription_status=Tenant.SubscriptionStatus.TRIAL,
    )
    assert tenant_has_messaging_access(tenant.pk) is False


@pytest.mark.django_db
def test_logout_whatsapp_session_keeps_instance_active():
    from apps.integrations.services.provisioning import logout_whatsapp_session

    tenant = TenantFactory()
    instance = WhatsappInstanceFactory(
        tenant=tenant,
        is_active=True,
        api_key="test-api-key",
        connection_status=WhatsappInstance.ConnectionStatus.OPEN,
    )

    with mock.patch(
        "apps.integrations.services.provisioning.EvolutionClient",
    ) as mock_cls:
        mock_cls.return_value.logout_instance.return_value = {}
        mock_cls.return_value.disconnect_remote_session.return_value = {}
        logout_whatsapp_session(instance)

    instance.refresh_from_db()
    assert instance.is_active is True
    assert instance.connection_status == WhatsappInstance.ConnectionStatus.CLOSE

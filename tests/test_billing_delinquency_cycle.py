"""Ciclo de inadimplência da assinatura SaaS (Asaas → tenant → painel/bot)."""

from __future__ import annotations

import uuid
from datetime import date, timedelta
from io import StringIO
from unittest import mock

import pytest
from django.core import mail
from django.core.management import call_command
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.billing.models import Subscription
from apps.billing.services.asaas_client import AsaasAPIError
from apps.billing.services.subscription_enforcement import (
    enforce_tenant_suspension,
    suspension_reason_for_tenant,
)
from apps.billing.services.tenant_suspension import tenant_has_messaging_access
from apps.billing.services.webhook_processor import process_asaas_webhook_payload
from apps.tenants.models import Tenant
from tests.factories import (
    SubscriptionFactory,
    TenantFactory,
    UserFactory,
    WhatsappInstanceFactory,
)

LOGOUT_PATH = "apps.billing.services.subscription_enforcement.logout_whatsapp_session"
PURCHASE_PATH = "apps.billing.services.webhook_processor.schedule_meta_purchase_event"
REGULARIZE_CLIENT_PATH = "apps.billing.services.regularization.AsaasClient"

VALID_CARD_BODY = {
    "credit_card": {
        "holderName": "Cliente Teste",
        "number": "4111111111111111",
        "expiryMonth": "12",
        "expiryYear": "2030",
        "ccv": "123",
    },
    "credit_card_holder": {
        "name": "Cliente Teste",
        "email": "cliente@example.com",
        "cpfCnpj": "24971563792",
        "postalCode": "01310100",
        "address": "Avenida Paulista",
        "addressNumber": "100",
        "province": "Bela Vista",
        "phone": "11999998888",
    },
}


def _auth_client(user) -> APIClient:
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(user).access_token}")
    return client


def _payment_event(
    event: str,
    sub: Subscription,
    *,
    payment_id: str,
    status: str,
    due: date,
    event_id: str | None = None,
) -> dict:
    """Envelope no formato documentado pelo Asaas (id do evento, dateCreated, payment completo)."""
    paid = status in {"CONFIRMED", "RECEIVED", "RECEIVED_IN_CASH"}
    return {
        "id": event_id or f"evt_{uuid.uuid4().hex}&{uuid.uuid4().int % 10**9}",
        "event": event,
        "dateCreated": timezone.localtime().strftime("%Y-%m-%d %H:%M:%S"),
        "payment": {
            "object": "payment",
            "id": payment_id,
            "customer": sub.asaas_customer_id,
            "subscription": sub.asaas_subscription_id,
            "dueDate": due.isoformat(),
            "originalDueDate": due.isoformat(),
            "value": 59.9,
            "billingType": "CREDIT_CARD",
            "status": status,
            "confirmedDate": due.isoformat() if paid else None,
            "paymentDate": due.isoformat() if paid else None,
            "deleted": False,
        },
    }


def _active_tenant_with_sub(**tenant_kwargs):
    defaults = {
        "trial_started_at": timezone.now() - timedelta(days=60),
        "trial_ends_at": timezone.now() - timedelta(days=53),
        "subscription_status": Tenant.SubscriptionStatus.ACTIVE,
    }
    defaults.update(tenant_kwargs)
    tenant = TenantFactory(**defaults)
    sub = SubscriptionFactory(tenant=tenant, status=Subscription.Status.ACTIVE)
    return tenant, sub


def _make_overdue(sub: Subscription, payment_id: str = "pay_current", due: date | None = None) -> None:
    due = due or timezone.localdate() - timedelta(days=1)
    process_asaas_webhook_payload(
        _payment_event("PAYMENT_OVERDUE", sub, payment_id=payment_id, status="OVERDUE", due=due),
    )


def _suspend_locally(tenant: Tenant) -> None:
    tenant.refresh_from_db()
    tenant.overdue_since = timezone.now() - timedelta(days=5)
    tenant.save(update_fields=["overdue_since"])
    with mock.patch(LOGOUT_PATH):
        assert enforce_tenant_suspension(tenant, reason="billing_overdue", send_email=False)
    tenant.refresh_from_db()
    assert tenant.subscription_status == Tenant.SubscriptionStatus.SUSPENDED


# ---------------------------------------------------------------------------
# Gap 1: evento de pagamento antigo, fora de ordem ou sem vínculo
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_old_payment_event_does_not_reactivate_overdue_tenant():
    tenant, sub = _active_tenant_with_sub()
    today = timezone.localdate()
    _make_overdue(sub, "pay_current", today - timedelta(days=1))
    tenant.refresh_from_db()
    assert tenant.subscription_status == Tenant.SubscriptionStatus.OVERDUE

    process_asaas_webhook_payload(
        _payment_event(
            "PAYMENT_RECEIVED",
            sub,
            payment_id="pay_previous_month",
            status="RECEIVED",
            due=today - timedelta(days=31),
        ),
    )

    tenant.refresh_from_db()
    assert tenant.subscription_status == Tenant.SubscriptionStatus.OVERDUE
    assert tenant.overdue_since is not None


@pytest.mark.django_db
def test_card_received_32_days_after_confirmed_does_not_reactivate_next_cycle():
    """Cartão: PAYMENT_RECEIVED chega ~32 dias após PAYMENT_CONFIRMED da mesma cobrança."""
    tenant, sub = _active_tenant_with_sub()
    today = timezone.localdate()
    old_due = today - timedelta(days=32)
    process_asaas_webhook_payload(
        _payment_event("PAYMENT_CONFIRMED", sub, payment_id="pay_m1", status="CONFIRMED", due=old_due),
    )
    _make_overdue(sub, "pay_m2", today - timedelta(days=1))

    process_asaas_webhook_payload(
        _payment_event("PAYMENT_RECEIVED", sub, payment_id="pay_m1", status="RECEIVED", due=old_due),
    )

    tenant.refresh_from_db()
    assert tenant.subscription_status == Tenant.SubscriptionStatus.OVERDUE


@pytest.mark.django_db
def test_payment_of_required_charge_reactivates_overdue_tenant():
    tenant, sub = _active_tenant_with_sub()
    due = timezone.localdate() - timedelta(days=1)
    _make_overdue(sub, "pay_current", due)

    process_asaas_webhook_payload(
        _payment_event("PAYMENT_CONFIRMED", sub, payment_id="pay_current", status="CONFIRMED", due=due),
    )

    tenant.refresh_from_db()
    sub.refresh_from_db()
    assert tenant.subscription_status == Tenant.SubscriptionStatus.ACTIVE
    assert tenant.overdue_since is None
    assert tenant.billing_blocked_at is None
    assert sub.status == Subscription.Status.ACTIVE


@pytest.mark.django_db
def test_late_overdue_event_after_payment_is_ignored():
    tenant, sub = _active_tenant_with_sub()
    due = timezone.localdate() - timedelta(days=1)
    process_asaas_webhook_payload(
        _payment_event("PAYMENT_CONFIRMED", sub, payment_id="pay_x", status="CONFIRMED", due=due),
    )
    process_asaas_webhook_payload(
        _payment_event("PAYMENT_OVERDUE", sub, payment_id="pay_x", status="OVERDUE", due=due),
    )

    tenant.refresh_from_db()
    assert tenant.subscription_status == Tenant.SubscriptionStatus.ACTIVE
    assert tenant.overdue_since is None


@pytest.mark.django_db
def test_old_payment_event_does_not_reactivate_suspended_tenant():
    tenant, sub = _active_tenant_with_sub()
    today = timezone.localdate()
    _make_overdue(sub, "pay_current", today - timedelta(days=5))
    _suspend_locally(tenant)

    process_asaas_webhook_payload(
        _payment_event(
            "PAYMENT_CONFIRMED",
            sub,
            payment_id="pay_previous_month",
            status="CONFIRMED",
            due=today - timedelta(days=35),
        ),
    )

    tenant.refresh_from_db()
    assert tenant.subscription_status == Tenant.SubscriptionStatus.SUSPENDED
    assert tenant.billing_blocked_at is not None


@pytest.mark.django_db
def test_payment_event_without_payment_id_does_not_reactivate():
    tenant = TenantFactory(
        subscription_status=Tenant.SubscriptionStatus.OVERDUE,
        overdue_since=timezone.now() - timedelta(days=2),
    )
    sub = SubscriptionFactory(tenant=tenant, status=Subscription.Status.OVERDUE)

    process_asaas_webhook_payload(
        {"event": "PAYMENT_RECEIVED", "payment": {"subscription": sub.asaas_subscription_id}},
    )

    tenant.refresh_from_db()
    assert tenant.subscription_status == Tenant.SubscriptionStatus.OVERDUE


@pytest.mark.django_db
def test_payment_event_never_reactivates_canceled_tenant():
    tenant, sub = _active_tenant_with_sub(
        subscription_status=Tenant.SubscriptionStatus.CANCELED,
        billing_blocked_at=timezone.now() - timedelta(days=1),
    )
    sub.status = Subscription.Status.CANCELLED
    sub.save(update_fields=["status"])

    process_asaas_webhook_payload(
        _payment_event(
            "PAYMENT_CONFIRMED",
            sub,
            payment_id="pay_after_cancel",
            status="CONFIRMED",
            due=timezone.localdate(),
        ),
    )

    tenant.refresh_from_db()
    assert tenant.subscription_status == Tenant.SubscriptionStatus.CANCELED
    assert tenant.billing_blocked_at is not None


@pytest.mark.django_db
def test_duplicate_webhook_delivery_is_processed_once():
    tenant, sub = _active_tenant_with_sub()
    due = timezone.localdate()
    payload = _payment_event(
        "PAYMENT_CONFIRMED", sub, payment_id="pay_dup", status="CONFIRMED", due=due,
    )

    with mock.patch(PURCHASE_PATH) as purchase:
        process_asaas_webhook_payload(payload)
        process_asaas_webhook_payload(payload)
        process_asaas_webhook_payload(
            _payment_event("PAYMENT_RECEIVED", sub, payment_id="pay_dup", status="RECEIVED", due=due),
        )

    assert purchase.call_count == 1


@pytest.mark.django_db
def test_credit_card_capture_refused_marks_charge_required():
    tenant, sub = _active_tenant_with_sub()
    due = timezone.localdate()
    process_asaas_webhook_payload(
        _payment_event(
            "PAYMENT_CREDIT_CARD_CAPTURE_REFUSED", sub, payment_id="pay_refused", status="PENDING", due=due,
        ),
    )

    tenant.refresh_from_db()
    assert tenant.subscription_status == Tenant.SubscriptionStatus.OVERDUE
    assert sub.charges.get(asaas_payment_id="pay_refused").is_outstanding


@pytest.mark.django_db
def test_overdue_event_does_not_downgrade_suspended_to_overdue():
    tenant, sub = _active_tenant_with_sub()
    _make_overdue(sub, "pay_current")
    _suspend_locally(tenant)

    _make_overdue(sub, "pay_next", timezone.localdate())

    tenant.refresh_from_db()
    assert tenant.subscription_status == Tenant.SubscriptionStatus.SUSPENDED


@pytest.mark.django_db
def test_payment_of_one_of_two_required_charges_keeps_tenant_overdue():
    tenant, sub = _active_tenant_with_sub()
    today = timezone.localdate()
    _make_overdue(sub, "pay_m1", today - timedelta(days=31))
    _make_overdue(sub, "pay_m2", today - timedelta(days=1))

    process_asaas_webhook_payload(
        _payment_event(
            "PAYMENT_CONFIRMED", sub, payment_id="pay_m2", status="CONFIRMED", due=today - timedelta(days=1),
        ),
    )
    tenant.refresh_from_db()
    assert tenant.subscription_status == Tenant.SubscriptionStatus.OVERDUE

    process_asaas_webhook_payload(
        _payment_event(
            "PAYMENT_CONFIRMED", sub, payment_id="pay_m1", status="CONFIRMED", due=today - timedelta(days=31),
        ),
    )
    tenant.refresh_from_db()
    assert tenant.subscription_status == Tenant.SubscriptionStatus.ACTIVE


@pytest.mark.django_db
def test_duplicate_payload_without_event_id_is_processed_once():
    tenant, sub = _active_tenant_with_sub()
    payload = _payment_event(
        "PAYMENT_CONFIRMED", sub, payment_id="pay_noid", status="CONFIRMED", due=timezone.localdate(),
    )
    payload.pop("id")

    from apps.billing.models import AsaasWebhookEvent

    process_asaas_webhook_payload(payload)
    process_asaas_webhook_payload(payload)

    assert AsaasWebhookEvent.objects.filter(asaas_payment_id="pay_noid").count() == 1


# ---------------------------------------------------------------------------
# Gap 2: cartão atualizado não quita a cobrança exigida
# ---------------------------------------------------------------------------


def _regularize_client_mock(mock_cls, *, payment_status="OVERDUE", pay_result=None, pay_error=None):
    inst = mock_cls.return_value
    inst.tokenize_credit_card.return_value = {"creditCardToken": "tok_123"}
    inst.update_subscription_credit_card.return_value = {}
    inst.get_payment.return_value = {"id": "pay_current", "status": payment_status}
    inst.list_payments.return_value = {"data": []}
    inst.get_subscription.return_value = {
        "status": "ACTIVE",
        "billingType": "CREDIT_CARD",
        "nextDueDate": timezone.localdate().isoformat(),
    }
    if pay_error is not None:
        inst.pay_with_credit_card.side_effect = pay_error
    else:
        inst.pay_with_credit_card.return_value = pay_result or {
            "id": "pay_current",
            "status": "CONFIRMED",
            "confirmedDate": timezone.localdate().isoformat(),
        }
    return inst


@pytest.mark.django_db
def test_card_update_alone_does_not_pay_or_release_suspended_tenant():
    tenant, sub = _active_tenant_with_sub()
    _make_overdue(sub, "pay_current")
    _suspend_locally(tenant)
    user = UserFactory(tenant=tenant)

    with mock.patch("apps.billing.services.payment_method.AsaasClient") as mock_cls:
        inst = _regularize_client_mock(mock_cls)
        response = _auth_client(user).post(
            reverse("settings-billing-payment-method"), VALID_CARD_BODY, format="json",
        )

    assert response.status_code == 200
    inst.pay_with_credit_card.assert_not_called()
    tenant.refresh_from_db()
    assert tenant.subscription_status == Tenant.SubscriptionStatus.SUSPENDED
    assert tenant.billing_blocked_at is not None


@pytest.mark.django_db
def test_regularize_pays_required_charge_and_releases_access():
    tenant, sub = _active_tenant_with_sub()
    _make_overdue(sub, "pay_current")
    _suspend_locally(tenant)
    user = UserFactory(tenant=tenant)

    with mock.patch(REGULARIZE_CLIENT_PATH) as mock_cls:
        inst = _regularize_client_mock(mock_cls)
        response = _auth_client(user).post(
            reverse("settings-billing-regularize"), VALID_CARD_BODY, format="json",
        )

    assert response.status_code == 200, response.content
    assert response.json()["status"] == "regularized"
    inst.update_subscription_credit_card.assert_called_once()
    inst.pay_with_credit_card.assert_called_once()
    assert inst.pay_with_credit_card.call_args[0][0] == "pay_current"
    tenant.refresh_from_db()
    assert tenant.subscription_status == Tenant.SubscriptionStatus.ACTIVE
    assert tenant.billing_blocked_at is None


@pytest.mark.django_db
def test_regularize_with_refused_card_keeps_block():
    tenant, sub = _active_tenant_with_sub()
    _make_overdue(sub, "pay_current")
    _suspend_locally(tenant)
    user = UserFactory(tenant=tenant)

    error = AsaasAPIError(
        "Erro na API Asaas",
        status_code=400,
        payload={"errors": [{"code": "invalid_creditCard", "description": "Cartão recusado."}]},
    )
    with mock.patch(REGULARIZE_CLIENT_PATH) as mock_cls:
        _regularize_client_mock(mock_cls, pay_error=error)
        response = _auth_client(user).post(
            reverse("settings-billing-regularize"), VALID_CARD_BODY, format="json",
        )

    # 422, não 402: o front trata 402 como bloqueio do middleware e redireciona.
    assert response.status_code == 422
    assert response.json()["code"] == "card_refused"
    assert response.json()["detail"] == "Cartão recusado."
    tenant.refresh_from_db()
    assert tenant.subscription_status == Tenant.SubscriptionStatus.SUSPENDED
    assert tenant.billing_blocked_at is not None


@pytest.mark.django_db
def test_regularize_awaiting_risk_analysis_keeps_block_until_confirmation():
    tenant, sub = _active_tenant_with_sub()
    _make_overdue(sub, "pay_current")
    _suspend_locally(tenant)
    user = UserFactory(tenant=tenant)

    with mock.patch(REGULARIZE_CLIENT_PATH) as mock_cls:
        _regularize_client_mock(
            mock_cls, pay_result={"id": "pay_current", "status": "AWAITING_RISK_ANALYSIS"},
        )
        response = _auth_client(user).post(
            reverse("settings-billing-regularize"), VALID_CARD_BODY, format="json",
        )

    assert response.status_code == 202
    assert response.json()["status"] == "pending_confirmation"
    tenant.refresh_from_db()
    assert tenant.subscription_status == Tenant.SubscriptionStatus.SUSPENDED


@pytest.mark.django_db
def test_regularize_does_not_charge_twice_when_charge_already_paid():
    tenant, sub = _active_tenant_with_sub()
    _make_overdue(sub, "pay_current")
    _suspend_locally(tenant)
    user = UserFactory(tenant=tenant)

    with mock.patch(REGULARIZE_CLIENT_PATH) as mock_cls:
        inst = _regularize_client_mock(mock_cls, payment_status="CONFIRMED")
        response = _auth_client(user).post(
            reverse("settings-billing-regularize"), VALID_CARD_BODY, format="json",
        )

    assert response.status_code == 200
    inst.pay_with_credit_card.assert_not_called()
    tenant.refresh_from_db()
    assert tenant.subscription_status == Tenant.SubscriptionStatus.ACTIVE


@pytest.mark.django_db
def test_regularize_without_identified_charge_does_not_release():
    tenant = TenantFactory(
        trial_started_at=timezone.now() - timedelta(days=60),
        trial_ends_at=timezone.now() - timedelta(days=53),
        subscription_status=Tenant.SubscriptionStatus.SUSPENDED,
        overdue_since=timezone.now() - timedelta(days=6),
        billing_blocked_at=timezone.now() - timedelta(days=2),
    )
    SubscriptionFactory(tenant=tenant, status=Subscription.Status.OVERDUE)
    user = UserFactory(tenant=tenant)

    with mock.patch(REGULARIZE_CLIENT_PATH) as mock_cls:
        inst = _regularize_client_mock(mock_cls)
        response = _auth_client(user).post(
            reverse("settings-billing-regularize"), VALID_CARD_BODY, format="json",
        )

    assert response.status_code == 409
    inst.pay_with_credit_card.assert_not_called()
    tenant.refresh_from_db()
    assert tenant.subscription_status == Tenant.SubscriptionStatus.SUSPENDED


@pytest.mark.django_db
def test_regularize_trial_expired_pays_first_pending_charge_from_asaas():
    tenant = TenantFactory(
        trial_started_at=timezone.now() - timedelta(days=8),
        trial_ends_at=timezone.now() - timedelta(hours=10),
        subscription_status=Tenant.SubscriptionStatus.TRIAL,
    )
    sub = SubscriptionFactory(tenant=tenant, status=Subscription.Status.ACTIVE)
    with mock.patch(LOGOUT_PATH):
        enforce_tenant_suspension(tenant, reason="trial_expired", send_email=False)
    user = UserFactory(tenant=tenant)

    def list_payments(**params):
        if params["status"] == "PENDING":
            return {
                "data": [
                    {
                        "id": "pay_first",
                        "subscription": sub.asaas_subscription_id,
                        "status": "PENDING",
                        "dueDate": timezone.localdate().isoformat(),
                    },
                ],
            }
        return {"data": []}

    with mock.patch(REGULARIZE_CLIENT_PATH) as mock_cls:
        inst = _regularize_client_mock(mock_cls, payment_status="PENDING")
        inst.list_payments.side_effect = list_payments
        inst.pay_with_credit_card.return_value = {"id": "pay_first", "status": "CONFIRMED"}
        response = _auth_client(user).post(
            reverse("settings-billing-regularize"), VALID_CARD_BODY, format="json",
        )

    assert response.status_code == 200, response.content
    assert inst.pay_with_credit_card.call_args[0][0] == "pay_first"
    tenant.refresh_from_db()
    assert tenant.subscription_status == Tenant.SubscriptionStatus.ACTIVE


@pytest.mark.django_db
def test_regularize_rejected_for_tenant_without_debt():
    tenant, _sub = _active_tenant_with_sub()
    user = UserFactory(tenant=tenant)

    with mock.patch(REGULARIZE_CLIENT_PATH) as mock_cls:
        inst = _regularize_client_mock(mock_cls)
        response = _auth_client(user).post(
            reverse("settings-billing-regularize"), VALID_CARD_BODY, format="json",
        )

    assert response.status_code == 409
    inst.tokenize_credit_card.assert_not_called()


@pytest.mark.django_db
def test_reactivation_refused_when_canceled_with_overdue_debt():
    tenant, sub = _active_tenant_with_sub()
    _make_overdue(sub, "pay_current")
    _suspend_locally(tenant)
    with mock.patch("apps.billing.services.subscription_cancel.AsaasClient"):
        from apps.billing.services.subscription_cancel import cancel_tenant_subscription

        cancel_tenant_subscription(tenant)
    tenant.refresh_from_db()
    assert tenant.subscription_status == Tenant.SubscriptionStatus.CANCELED
    user = UserFactory(tenant=tenant)
    from tests.factories import MarketFactory

    MarketFactory(tenant=tenant)

    with mock.patch("apps.billing.services.subscription_reactivate.AsaasClient") as mock_cls:
        response = _auth_client(user).post(reverse("settings-billing-reactivate-subscription"))

    assert response.status_code == 409
    assert response.json()["code"] == "outstanding_debt"
    mock_cls.return_value.update_subscription.assert_not_called()
    mock_cls.return_value.create_subscription.assert_not_called()
    tenant.refresh_from_db()
    assert tenant.subscription_status == Tenant.SubscriptionStatus.CANCELED


# ---------------------------------------------------------------------------
# Gap 3: tenant CANCELED após o trial ainda com acesso ao bot
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_canceled_after_trial_has_no_messaging_access():
    tenant = TenantFactory(
        trial_started_at=timezone.now() - timedelta(days=10),
        trial_ends_at=timezone.now() - timedelta(days=3),
        subscription_status=Tenant.SubscriptionStatus.CANCELED,
        billing_blocked_at=None,
    )
    assert tenant_has_messaging_access(tenant.pk) is False


@pytest.mark.django_db
def test_canceled_during_trial_keeps_messaging_until_trial_end():
    tenant = TenantFactory(
        trial_ends_at=timezone.now() + timedelta(days=2),
        subscription_status=Tenant.SubscriptionStatus.CANCELED,
    )
    assert tenant_has_messaging_access(tenant.pk) is True


@pytest.mark.django_db
def test_check_subscriptions_blocks_canceled_tenant_after_trial():
    tenant = TenantFactory(
        trial_started_at=timezone.now() - timedelta(days=10),
        trial_ends_at=timezone.now() - timedelta(days=3),
        subscription_status=Tenant.SubscriptionStatus.CANCELED,
    )
    WhatsappInstanceFactory(tenant=tenant, is_active=True)

    with mock.patch(LOGOUT_PATH) as logout:
        call_command("check_subscriptions", stdout=StringIO())

    tenant.refresh_from_db()
    assert tenant.subscription_status == Tenant.SubscriptionStatus.CANCELED
    assert tenant.billing_blocked_at is not None
    logout.assert_called_once()


@pytest.mark.django_db
def test_cancel_after_trial_blocks_and_schedules_logout():
    tenant, _sub = _active_tenant_with_sub()
    with mock.patch("apps.billing.services.subscription_cancel.AsaasClient"):
        from apps.billing.services.subscription_cancel import cancel_tenant_subscription

        cancel_tenant_subscription(tenant)

    tenant.refresh_from_db()
    assert tenant.billing_blocked_at is not None
    assert tenant.whatsapp_logout_pending_since is not None
    assert tenant_has_messaging_access(tenant.pk) is False


@pytest.mark.django_db
def test_check_subscriptions_dry_run_changes_nothing():
    tenant = TenantFactory(
        trial_ends_at=timezone.now() - timedelta(days=1),
        subscription_status=Tenant.SubscriptionStatus.TRIAL,
    )
    out = StringIO()
    with mock.patch(LOGOUT_PATH) as logout:
        call_command("check_subscriptions", "--dry-run", stdout=out)

    logout.assert_not_called()
    tenant.refresh_from_db()
    assert tenant.subscription_status == Tenant.SubscriptionStatus.TRIAL
    assert f"tenant_id={tenant.pk}" in out.getvalue()


# ---------------------------------------------------------------------------
# Gap 4: falha no logout Evolution não pode adiar o bloqueio local
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_logout_failure_still_blocks_locally_and_records_pending_logout():
    tenant = TenantFactory(
        trial_ends_at=timezone.now() - timedelta(days=1),
        subscription_status=Tenant.SubscriptionStatus.TRIAL,
    )
    WhatsappInstanceFactory(tenant=tenant, is_active=True)

    with mock.patch(LOGOUT_PATH, side_effect=TimeoutError("evolution down")):
        ok = enforce_tenant_suspension(tenant, reason="trial_expired", send_email=False)

    assert ok is True
    tenant.refresh_from_db()
    assert tenant.subscription_status == Tenant.SubscriptionStatus.SUSPENDED
    assert tenant.billing_blocked_at is not None
    assert tenant.whatsapp_logout_pending_since is not None
    assert tenant.whatsapp_logout_attempts == 1
    assert "evolution down" in tenant.whatsapp_logout_last_error
    assert tenant_has_messaging_access(tenant.pk) is False


@pytest.mark.django_db
def test_check_subscriptions_retries_pending_logout_observably():
    tenant = TenantFactory(
        trial_ends_at=timezone.now() - timedelta(days=1),
        subscription_status=Tenant.SubscriptionStatus.TRIAL,
    )
    WhatsappInstanceFactory(tenant=tenant, is_active=True)
    with mock.patch(LOGOUT_PATH, side_effect=TimeoutError("evolution down")):
        enforce_tenant_suspension(tenant, reason="trial_expired", send_email=False)

    out, err = StringIO(), StringIO()
    with mock.patch(LOGOUT_PATH, side_effect=TimeoutError("still down")):
        call_command("check_subscriptions", stdout=out, stderr=err)
    tenant.refresh_from_db()
    assert tenant.whatsapp_logout_attempts == 2
    assert "still down" in tenant.whatsapp_logout_last_error
    assert f"tenant_id={tenant.pk}" in err.getvalue()

    with mock.patch(LOGOUT_PATH) as logout:
        call_command("check_subscriptions", stdout=StringIO(), stderr=StringIO())
    logout.assert_called_once()
    tenant.refresh_from_db()
    assert tenant.whatsapp_logout_pending_since is None
    assert tenant.subscription_status == Tenant.SubscriptionStatus.SUSPENDED


@pytest.mark.django_db
def test_new_suspension_starts_logout_attempts_from_zero():
    tenant = TenantFactory(
        subscription_status=Tenant.SubscriptionStatus.OVERDUE,
        overdue_since=timezone.now() - timedelta(days=10),
        whatsapp_logout_attempts=3,
        whatsapp_logout_last_attempt_at=timezone.now() - timedelta(days=30),
        whatsapp_logout_last_error="RuntimeError: bloqueio anterior",
    )
    WhatsappInstanceFactory(tenant=tenant, is_active=True)

    with mock.patch(LOGOUT_PATH, side_effect=TimeoutError("evolution down")):
        assert enforce_tenant_suspension(tenant, reason="billing_overdue", send_email=False) is True

    tenant.refresh_from_db()
    assert tenant.whatsapp_logout_pending_since is not None
    assert tenant.whatsapp_logout_attempts == 1
    assert "evolution down" in tenant.whatsapp_logout_last_error
    assert "bloqueio anterior" not in tenant.whatsapp_logout_last_error


@pytest.mark.django_db
def test_regularization_cancels_pending_logout():
    tenant, sub = _active_tenant_with_sub()
    WhatsappInstanceFactory(tenant=tenant, is_active=True)
    due = timezone.localdate() - timedelta(days=5)
    _make_overdue(sub, "pay_current", due)
    tenant.refresh_from_db()
    tenant.overdue_since = timezone.now() - timedelta(days=5)
    tenant.save(update_fields=["overdue_since"])
    with mock.patch(LOGOUT_PATH, side_effect=TimeoutError("evolution down")):
        enforce_tenant_suspension(tenant, reason="billing_overdue", send_email=False)

    process_asaas_webhook_payload(
        _payment_event("PAYMENT_CONFIRMED", sub, payment_id="pay_current", status="CONFIRMED", due=due),
    )
    tenant.refresh_from_db()
    assert tenant.subscription_status == Tenant.SubscriptionStatus.ACTIVE
    assert tenant.whatsapp_logout_pending_since is None

    with mock.patch(LOGOUT_PATH) as logout:
        call_command("check_subscriptions", stdout=StringIO(), stderr=StringIO())
    logout.assert_not_called()


@pytest.mark.django_db
def test_panel_request_suspends_locally_without_calling_evolution():
    tenant = TenantFactory(
        trial_started_at=timezone.now() - timedelta(days=30),
        trial_ends_at=timezone.now() - timedelta(days=20),
        subscription_status=Tenant.SubscriptionStatus.OVERDUE,
        overdue_since=timezone.now() - timedelta(days=4),
    )
    SubscriptionFactory(tenant=tenant, status=Subscription.Status.OVERDUE)
    WhatsappInstanceFactory(tenant=tenant, is_active=True)
    user = UserFactory(tenant=tenant)

    with mock.patch(LOGOUT_PATH) as logout:
        response = _auth_client(user).get(reverse("products-list"))

    assert response.status_code == 402
    logout.assert_not_called()
    tenant.refresh_from_db()
    assert tenant.subscription_status == Tenant.SubscriptionStatus.SUSPENDED
    assert tenant.whatsapp_logout_pending_since is not None


def _suspended_by_panel_request() -> tuple[Tenant, object]:
    tenant = TenantFactory(
        trial_started_at=timezone.now() - timedelta(days=30),
        trial_ends_at=timezone.now() - timedelta(days=20),
        subscription_status=Tenant.SubscriptionStatus.OVERDUE,
        overdue_since=timezone.now() - timedelta(days=4),
    )
    SubscriptionFactory(tenant=tenant, status=Subscription.Status.OVERDUE)
    user = UserFactory(tenant=tenant)
    assert _auth_client(user).get(reverse("products-list")).status_code == 402
    tenant.refresh_from_db()
    return tenant, user


@pytest.mark.django_db
def test_suspension_by_panel_request_gets_email_from_next_check():
    tenant, user = _suspended_by_panel_request()
    assert mail.outbox == []
    assert tenant.billing_suspension_notified_at is None

    with mock.patch(LOGOUT_PATH):
        call_command("check_subscriptions", stdout=StringIO(), stderr=StringIO())
        call_command("check_subscriptions", stdout=StringIO(), stderr=StringIO())

    assert [m.to for m in mail.outbox] == [[user.email]]
    tenant.refresh_from_db()
    assert tenant.billing_suspension_notified_at >= tenant.billing_blocked_at


@pytest.mark.django_db
def test_check_subscriptions_dry_run_lists_pending_email_without_sending():
    tenant, _ = _suspended_by_panel_request()
    out = StringIO()

    call_command("check_subscriptions", "--dry-run", stdout=out)

    assert "1 e-mail(s) de suspensão pendente(s)" in out.getvalue()
    assert f"tenant_id={tenant.pk}" in out.getvalue()
    assert mail.outbox == []
    tenant.refresh_from_db()
    assert tenant.billing_suspension_notified_at is None


@pytest.mark.django_db
def test_failed_suspension_email_stays_pending_until_sent():
    tenant = TenantFactory(
        trial_started_at=timezone.now() - timedelta(days=30),
        trial_ends_at=timezone.now() - timedelta(days=20),
        subscription_status=Tenant.SubscriptionStatus.OVERDUE,
        overdue_since=timezone.now() - timedelta(days=4),
    )
    UserFactory(tenant=tenant)
    err = StringIO()

    with mock.patch(LOGOUT_PATH), mock.patch(
        "apps.core.emails.send_subscription_suspended_email",
        side_effect=ConnectionRefusedError("smtp down"),
    ):
        call_command("check_subscriptions", stdout=StringIO(), stderr=err)

    tenant.refresh_from_db()
    assert tenant.subscription_status == Tenant.SubscriptionStatus.SUSPENDED
    assert tenant.billing_suspension_notified_at is None
    assert f"E-mail de suspensão pendente: tenant_id={tenant.pk}" in err.getvalue()

    with mock.patch(LOGOUT_PATH):
        call_command("check_subscriptions", stdout=StringIO(), stderr=StringIO())

    assert len(mail.outbox) == 1
    tenant.refresh_from_db()
    assert tenant.billing_suspension_notified_at is not None


@pytest.mark.django_db
def test_new_block_after_regularization_is_notified_again():
    blocked_at = timezone.now() - timedelta(hours=1)
    tenant = TenantFactory(
        subscription_status=Tenant.SubscriptionStatus.SUSPENDED,
        overdue_since=timezone.now() - timedelta(days=5),
        billing_blocked_at=blocked_at,
        billing_suspension_notified_at=blocked_at - timedelta(days=40),
    )
    UserFactory(tenant=tenant)

    with mock.patch(LOGOUT_PATH):
        call_command("check_subscriptions", stdout=StringIO(), stderr=StringIO())

    assert len(mail.outbox) == 1
    tenant.refresh_from_db()
    assert tenant.billing_suspension_notified_at >= blocked_at


@pytest.mark.django_db
def test_suspension_already_notified_is_not_emailed_again():
    blocked_at = timezone.now() - timedelta(hours=1)
    tenant = TenantFactory(
        subscription_status=Tenant.SubscriptionStatus.SUSPENDED,
        overdue_since=timezone.now() - timedelta(days=5),
        billing_blocked_at=blocked_at,
        billing_suspension_notified_at=blocked_at,
    )
    UserFactory(tenant=tenant)

    with mock.patch(LOGOUT_PATH):
        call_command("check_subscriptions", stdout=StringIO(), stderr=StringIO())

    assert mail.outbox == []


# ---------------------------------------------------------------------------
# Gap 5: limite da carência único para painel, bot e check_subscriptions
# ---------------------------------------------------------------------------


@pytest.mark.django_db
@pytest.mark.parametrize("offset", [timedelta(minutes=-1), timedelta(minutes=1)])
def test_grace_limit_is_consistent_across_panel_bot_and_enforcement(settings, offset):
    settings.BILLING_GRACE_DAYS = 3
    tenant = TenantFactory(
        trial_started_at=timezone.now() - timedelta(days=30),
        trial_ends_at=timezone.now() - timedelta(days=20),
        subscription_status=Tenant.SubscriptionStatus.OVERDUE,
        overdue_since=timezone.now() - timedelta(days=3) - offset,
    )
    eligible = suspension_reason_for_tenant(tenant) == "billing_overdue"
    in_grace = tenant.is_in_grace_period()
    messaging = tenant_has_messaging_access(tenant.pk)

    assert eligible is (offset > timedelta(0))
    assert in_grace is (not eligible)
    assert messaging is (not eligible)


def test_grace_deadline_rule(settings):
    from apps.tenants.billing_rules import grace_deadline, is_within_grace

    settings.BILLING_GRACE_DAYS = 3
    since = timezone.now() - timedelta(days=10)
    deadline = grace_deadline(since)
    assert deadline == since + timedelta(days=3)
    assert is_within_grace(since, now=deadline - timedelta(seconds=1)) is True
    assert is_within_grace(since, now=deadline) is False
    assert is_within_grace(None, now=deadline) is False


@pytest.mark.django_db
def test_auth_me_exposes_grace_deadline():
    since = timezone.now() - timedelta(days=1)
    tenant = TenantFactory(
        trial_started_at=timezone.now() - timedelta(days=30),
        trial_ends_at=timezone.now() - timedelta(days=20),
        subscription_status=Tenant.SubscriptionStatus.OVERDUE,
        overdue_since=since,
    )
    SubscriptionFactory(tenant=tenant, status=Subscription.Status.OVERDUE)
    user = UserFactory(tenant=tenant)

    body = _auth_client(user).get(reverse("auth-me")).json()

    assert body["is_in_grace_period"] is True
    assert body["grace_ends_at"] is not None

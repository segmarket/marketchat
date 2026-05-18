import pytest
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.notifications.models import Notification
from apps.notifications.services import create_critical_panel_notification
from apps.sales.services.intent_gatekeeper import MAINTENANCE_ISSUE, PAYMENT_ERROR
from tests.factories import MarketFactory, ResidentFactory, TenantFactory, UserFactory


def _auth(client, user):
    client.credentials(
        HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(user).access_token}",
    )


@pytest.mark.django_db
def test_create_critical_panel_notification_payment_error():
    tenant = TenantFactory()
    market = MarketFactory(tenant=tenant, name="Pamplona")
    resident = ResidentFactory(tenant=tenant, market=market, name="Maria Silva")

    note = create_critical_panel_notification(
        tenant_id=tenant.id,
        resident=resident,
        intent_type=PAYMENT_ERROR,
        original_message="A maquininha não passou o cartão",
    )

    assert note is not None
    assert note.severity == Notification.Severity.CRITICAL
    assert note.is_read is False
    assert note.intent_type == PAYMENT_ERROR
    assert note.market_id == market.id
    assert "pagamento" in note.title.lower()
    assert "Maria Silva" in note.message
    assert "Pamplona" in note.message


@pytest.mark.django_db
def test_create_critical_panel_notification_dedup_within_window():
    tenant = TenantFactory()
    market = MarketFactory(tenant=tenant)
    resident = ResidentFactory(tenant=tenant, market=market)

    first = create_critical_panel_notification(
        tenant_id=tenant.id,
        resident=resident,
        intent_type=MAINTENANCE_ISSUE,
        original_message="Lâmpada queimada",
    )
    second = create_critical_panel_notification(
        tenant_id=tenant.id,
        resident=resident,
        intent_type=MAINTENANCE_ISSUE,
        original_message="Lâmpada queimada de novo",
    )

    assert first is not None
    assert second is None
    assert Notification.all_objects.filter(tenant=tenant, is_read=False).count() == 1


@pytest.mark.django_db
def test_latest_returns_only_current_tenant_unread():
    tenant_a = TenantFactory()
    tenant_b = TenantFactory()
    user_a = UserFactory(tenant=tenant_a)
    market_a = MarketFactory(tenant=tenant_a, name="Mercado A")

    Notification.all_objects.create(
        tenant=tenant_a,
        market=market_a,
        title="Alerta A",
        message="Msg A",
        severity=Notification.Severity.CRITICAL,
        is_read=False,
    )
    Notification.all_objects.create(
        tenant=tenant_b,
        market=MarketFactory(tenant=tenant_b),
        title="Alerta B",
        message="Msg B",
        severity=Notification.Severity.CRITICAL,
        is_read=False,
    )
    Notification.all_objects.create(
        tenant=tenant_a,
        market=market_a,
        title="Lida",
        message="Msg lida",
        severity=Notification.Severity.INFO,
        is_read=True,
    )

    url = reverse("notifications-latest")
    client = APIClient()
    _auth(client, user_a)
    response = client.get(url)

    assert response.status_code == 200
    assert response.data["unread_count"] == 1
    assert len(response.data["results"]) == 1
    assert response.data["results"][0]["title"] == "Alerta A"
    assert response.data["results"][0]["market_name"] == "Mercado A"


@pytest.mark.django_db
def test_read_notification_tenant_isolation():
    tenant_a = TenantFactory()
    tenant_b = TenantFactory()
    user_a = UserFactory(tenant=tenant_a)
    note_b = Notification.all_objects.create(
        tenant=tenant_b,
        title="Outro tenant",
        message="Secret",
        severity=Notification.Severity.CRITICAL,
    )

    client = APIClient()
    _auth(client, user_a)
    url = reverse("notifications-read", kwargs={"pk": note_b.pk})
    response = client.post(url)

    assert response.status_code == 404
    note_b.refresh_from_db()
    assert note_b.is_read is False


@pytest.mark.django_db
def test_read_all_only_affects_own_tenant():
    tenant_a = TenantFactory()
    tenant_b = TenantFactory()
    user_a = UserFactory(tenant=tenant_a)

    Notification.all_objects.create(
        tenant=tenant_a,
        title="A1",
        message="m",
        severity=Notification.Severity.CRITICAL,
        is_read=False,
    )
    note_b = Notification.all_objects.create(
        tenant=tenant_b,
        title="B1",
        message="m",
        severity=Notification.Severity.CRITICAL,
        is_read=False,
    )

    client = APIClient()
    _auth(client, user_a)
    response = client.post(reverse("notifications-read-all"))

    assert response.status_code == 200
    assert response.data["marked_read"] == 1
    note_b.refresh_from_db()
    assert note_b.is_read is False


@pytest.mark.django_db
def test_mark_single_notification_read():
    tenant = TenantFactory()
    user = UserFactory(tenant=tenant)
    note = Notification.all_objects.create(
        tenant=tenant,
        title="Teste",
        message="Corpo",
        severity=Notification.Severity.WARNING,
        is_read=False,
    )

    client = APIClient()
    _auth(client, user)
    url = reverse("notifications-read", kwargs={"pk": note.pk})
    response = client.post(url)

    assert response.status_code == 200
    assert response.data["is_read"] is True
    note.refresh_from_db()
    assert note.is_read is True

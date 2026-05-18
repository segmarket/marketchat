import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.integrations.models import WhatsappInstance
from apps.onboarding.models import TenantOnboarding
from apps.sales.models import Cart
from tests.factories import (
    CartFactory,
    MarketFactory,
    ProductFactory,
    ResidentFactory,
    TenantFactory,
    UserFactory,
    WhatsappInstanceFactory,
)


def _auth(client, user):
    client.credentials(
        HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(user).access_token}",
    )


@pytest.mark.django_db
def test_status_syncs_market_step():
    tenant = TenantFactory()
    user = UserFactory(tenant=tenant)
    MarketFactory(tenant=tenant)

    client = APIClient()
    _auth(client, user)
    response = client.get(reverse("onboarding-status"))

    assert response.status_code == 200
    assert response.data["step_market_created"] is True
    assert response.data["completed_count"] == 1
    assert response.data["completion_percent"] == 25
    assert response.data["show_mission_panel"] is True


@pytest.mark.django_db
def test_status_syncs_product_step_with_any_product():
    tenant = TenantFactory()
    user = UserFactory(tenant=tenant)
    ProductFactory(tenant=tenant, search_aliases="")

    client = APIClient()
    _auth(client, user)
    response = client.get(reverse("onboarding-status"))

    assert response.data["step_product_created"] is True


@pytest.mark.django_db
def test_status_full_completion_and_dismiss():
    tenant = TenantFactory()
    user = UserFactory(tenant=tenant)
    market = MarketFactory(tenant=tenant)
    ProductFactory(tenant=tenant, search_aliases="refrigerante")
    WhatsappInstanceFactory(
        tenant=tenant,
        connection_status=WhatsappInstance.ConnectionStatus.OPEN,
    )
    resident = ResidentFactory(tenant=tenant, market=market)
    cart = CartFactory(tenant=tenant, resident=resident, status=Cart.Status.COMPLETED)
    cart.product_photo.save(
        "audit.jpg",
        SimpleUploadedFile("audit.jpg", b"fake", content_type="image/jpeg"),
        save=True,
    )

    client = APIClient()
    _auth(client, user)
    status_resp = client.get(reverse("onboarding-status"))
    assert status_resp.data["completion_percent"] == 100

    dismiss_resp = client.post(reverse("onboarding-dismiss"))
    assert dismiss_resp.status_code == 200
    assert dismiss_resp.data["onboarding_finished"] is True
    assert dismiss_resp.data["show_mission_panel"] is False


@pytest.mark.django_db
def test_dismiss_blocked_before_completion():
    tenant = TenantFactory()
    user = UserFactory(tenant=tenant)

    client = APIClient()
    _auth(client, user)
    response = client.post(reverse("onboarding-dismiss"))

    assert response.status_code == 400


@pytest.mark.django_db
def test_tenant_isolation():
    tenant_a = TenantFactory()
    tenant_b = TenantFactory()
    user_a = UserFactory(tenant=tenant_a)
    MarketFactory(tenant=tenant_b)

    client = APIClient()
    _auth(client, user_a)
    response = client.get(reverse("onboarding-status"))

    assert response.data["step_market_created"] is False


@pytest.mark.django_db
def test_steps_do_not_regress_when_data_removed():
    tenant = TenantFactory()
    user = UserFactory(tenant=tenant)
    market = MarketFactory(tenant=tenant)

    record = TenantOnboarding.objects.create(
        tenant=tenant,
        step_market_created=True,
    )
    market.delete()

    client = APIClient()
    _auth(client, user)
    response = client.get(reverse("onboarding-status"))

    assert response.data["step_market_created"] is True
    record.refresh_from_db()
    assert record.step_market_created is True

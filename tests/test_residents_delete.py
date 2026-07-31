from __future__ import annotations

import pytest
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.residents.models import Resident
from apps.tenants.context import tenant_scope
from tests.factories import MarketFactory, ResidentFactory, TenantFactory, UserFactory


def _auth(client: APIClient, user) -> None:
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(user).access_token}")


@pytest.mark.django_db
def test_delete_resident_anonymizes_and_hides_from_list(api_client: APIClient):
    tenant = TenantFactory()
    market = MarketFactory(tenant=tenant)
    admin = UserFactory(tenant=tenant, email="admin-del@example.com", is_tenant_admin=True)
    resident = ResidentFactory(
        tenant=tenant,
        market=market,
        name="Maria Silva",
        phone_number="5511999000111",
    )

    _auth(api_client, admin)
    with tenant_scope(tenant.id):
        response = api_client.delete(reverse("residents-detail", kwargs={"pk": resident.pk}))

    assert response.status_code == 204
    resident.refresh_from_db()
    assert resident.is_anonymized is True
    assert resident.is_active is False

    with tenant_scope(tenant.id):
        listing = api_client.get(reverse("residents-list"))
    assert listing.status_code == 200
    ids = [row["id"] for row in listing.data]
    assert resident.pk not in ids


@pytest.mark.django_db
def test_delete_resident_cross_tenant_returns_404(api_client: APIClient):
    tenant_a = TenantFactory()
    tenant_b = TenantFactory()
    market_b = MarketFactory(tenant=tenant_b)
    admin_a = UserFactory(tenant=tenant_a, email="admin-a@example.com", is_tenant_admin=True)
    resident_b = ResidentFactory(
        tenant=tenant_b,
        market=market_b,
        phone_number="5511888000222",
    )

    _auth(api_client, admin_a)
    with tenant_scope(tenant_a.id):
        response = api_client.delete(reverse("residents-detail", kwargs={"pk": resident_b.pk}))

    assert response.status_code == 404
    resident_b.refresh_from_db()
    assert resident_b.is_anonymized is False


@pytest.mark.django_db
def test_delete_resident_non_admin_forbidden(api_client: APIClient):
    tenant = TenantFactory()
    market = MarketFactory(tenant=tenant)
    user = UserFactory(tenant=tenant, email="staff@example.com", is_tenant_admin=False)
    resident = ResidentFactory(tenant=tenant, market=market, phone_number="5511777000333")

    _auth(api_client, user)
    with tenant_scope(tenant.id):
        response = api_client.delete(reverse("residents-detail", kwargs={"pk": resident.pk}))

    assert response.status_code == 403
    resident.refresh_from_db()
    assert resident.is_anonymized is False

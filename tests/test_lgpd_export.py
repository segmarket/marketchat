import json

import pytest
from django.urls import reverse
from rest_framework_simplejwt.tokens import RefreshToken

from tests.factories import MarketFactory, ResidentFactory, TenantFactory, UserFactory


def _auth(client, user):
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(user).access_token}")


@pytest.mark.django_db
def test_tenant_export_returns_json(api_client):
    tenant = TenantFactory()
    user = UserFactory(tenant=tenant, is_tenant_admin=True)
    MarketFactory(tenant=tenant)

    url = reverse("lgpd-tenant-export")
    _auth(api_client, user)
    response = api_client.get(url)

    assert response.status_code == 200
    assert "attachment" in response["Content-Disposition"]
    data = json.loads(response.content.decode("utf-8"))
    assert data["export_type"] == "tenant"
    assert data["tenant"]["slug"] == tenant.slug
    assert data["user"]["email"] == user.email


@pytest.mark.django_db
def test_resident_export_isolated_by_tenant(api_client):
    tenant_a = TenantFactory()
    tenant_b = TenantFactory()
    user_b = UserFactory(tenant=tenant_b, is_tenant_admin=True)
    market_a = MarketFactory(tenant=tenant_a)
    resident_a = ResidentFactory(tenant=tenant_a, market=market_a)

    url = reverse("lgpd-resident-export", kwargs={"pk": resident_a.id})
    _auth(api_client, user_b)
    response = api_client.get(url)

    assert response.status_code == 404

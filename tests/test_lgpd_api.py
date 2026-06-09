import pytest
from django.urls import reverse
from rest_framework_simplejwt.tokens import RefreshToken

from apps.residents.models import Resident
from tests.factories import MarketFactory, ResidentFactory, TenantFactory, UserFactory


def _auth(client, user):
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(user).access_token}")


@pytest.mark.django_db
def test_anonymize_api_requires_admin(api_client):
    tenant = TenantFactory()
    market = MarketFactory(tenant=tenant)
    user = UserFactory(tenant=tenant, is_tenant_admin=False)
    ResidentFactory(tenant=tenant, market=market, phone_number="5511999001122")

    url = reverse("lgpd-resident-anonymize")
    _auth(api_client, user)
    response = api_client.post(url, {"phone": "11999001122"}, format="json")

    assert response.status_code == 403


@pytest.mark.django_db
def test_anonymize_api_by_phone(api_client):
    tenant = TenantFactory()
    market = MarketFactory(tenant=tenant)
    user = UserFactory(tenant=tenant, is_tenant_admin=True)
    resident = ResidentFactory(tenant=tenant, market=market, phone_number="5511999001122", name="Eva")

    url = reverse("lgpd-resident-anonymize")
    _auth(api_client, user)
    response = api_client.post(url, {"phone": "(11) 99900-1122"}, format="json")

    assert response.status_code == 200
    resident.refresh_from_db()
    assert resident.is_anonymized is True

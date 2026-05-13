import pytest
from django.urls import reverse
from rest_framework_simplejwt.tokens import RefreshToken

from tests.factories import TenantFactory, UserFactory


@pytest.mark.django_db
def test_auth_me_returns_user_and_tenant(api_client):
    tenant = TenantFactory(name="Acme")
    user = UserFactory(tenant=tenant, email="me@test.com", first_name="Ada", last_name="Test")
    url = reverse("auth-me")
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(user).access_token}")
    response = api_client.get(url)
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "me@test.com"
    assert data["tenant"]["name"] == "Acme"
    assert data["billing_blocked"] is False

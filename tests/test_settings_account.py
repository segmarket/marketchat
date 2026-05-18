import pytest
from django.urls import reverse
from rest_framework_simplejwt.tokens import RefreshToken

from tests.factories import TenantFactory, UserFactory


@pytest.mark.django_db
def test_settings_account_get(api_client):
    tenant = TenantFactory(cpf_cnpj="12345678901", phone="11988887777")
    user = UserFactory(tenant=tenant, email="admin@settings.com", first_name="Ana")
    url = reverse("settings-account")
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(user).access_token}")
    response = api_client.get(url)
    assert response.status_code == 200
    data = response.json()
    assert data["user"]["email"] == "admin@settings.com"
    assert data["user"]["first_name"] == "Ana"
    assert data["tenant"]["cpf_cnpj"] == "12345678901"
    assert data["tenant"]["cpf_cnpj_editable"] is False


@pytest.mark.django_db
def test_settings_account_patch_user_fields(api_client):
    tenant = TenantFactory()
    user = UserFactory(tenant=tenant, email="patch@settings.com")
    url = reverse("settings-account")
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(user).access_token}")
    response = api_client.patch(
        url,
        {"first_name": "Novo", "phone": "11911112222"},
        format="json",
    )
    assert response.status_code == 200
    user.refresh_from_db()
    assert user.first_name == "Novo"
    assert user.phone == "11911112222"


@pytest.mark.django_db
def test_settings_account_non_admin_cannot_patch_tenant(api_client):
    tenant = TenantFactory()
    user = UserFactory(tenant=tenant, email="member@settings.com", is_tenant_admin=False)
    url = reverse("settings-account")
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(user).access_token}")
    response = api_client.patch(url, {"tenant_name": "Hackeado"}, format="json")
    assert response.status_code == 400
    tenant.refresh_from_db()
    assert tenant.name != "Hackeado"


@pytest.mark.django_db
def test_settings_account_cpf_cnpj_immutable_after_set(api_client):
    tenant = TenantFactory(cpf_cnpj="11122233344")
    user = UserFactory(tenant=tenant, email="cpf@settings.com")
    url = reverse("settings-account")
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(user).access_token}")
    response = api_client.patch(url, {"cpf_cnpj": "99988877766"}, format="json")
    assert response.status_code == 400
    tenant.refresh_from_db()
    assert tenant.cpf_cnpj == "11122233344"


@pytest.mark.django_db
def test_settings_account_admin_can_set_cpf_once(api_client):
    tenant = TenantFactory(cpf_cnpj="")
    user = UserFactory(tenant=tenant, email="once@settings.com")
    url = reverse("settings-account")
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(user).access_token}")
    response = api_client.patch(
        url,
        {"cpf_cnpj": "24971563792", "tenant_name": "Nova Empresa"},
        format="json",
    )
    assert response.status_code == 200
    tenant.refresh_from_db()
    assert tenant.cpf_cnpj == "24971563792"
    assert tenant.name == "Nova Empresa"

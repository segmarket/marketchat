import pytest
from django.urls import reverse
from rest_framework_simplejwt.tokens import RefreshToken

from apps.products.models import Product
from tests.factories import ProductFactory, TenantFactory, UserFactory


def _auth(client, user):
    client.credentials(
        HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(user).access_token}",
    )


@pytest.mark.django_db
def test_products_search_empty_q(api_client):
    tenant = TenantFactory()
    user = UserFactory(tenant=tenant, email="prod-search-empty@example.com")
    ProductFactory(tenant=tenant, name="Refrigerante", status=Product.Status.ACTIVE)
    _auth(api_client, user)
    resp = api_client.get(reverse("products-search"), {"q": "a"})
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.django_db
def test_products_search_by_name(api_client):
    tenant = TenantFactory()
    other = TenantFactory(slug="other-tenant")
    user = UserFactory(tenant=tenant, email="prod-search@example.com")
    match = ProductFactory(
        tenant=tenant,
        name="Refrigerante Cola",
        price="5.50",
        status=Product.Status.ACTIVE,
    )
    ProductFactory(
        tenant=tenant,
        name="Água",
        status=Product.Status.ACTIVE,
    )
    ProductFactory(
        tenant=tenant,
        name="Refrigerante Zero",
        status=Product.Status.INACTIVE,
    )
    ProductFactory(
        tenant=other,
        name="Refrigerante Outro Tenant",
        status=Product.Status.ACTIVE,
    )

    _auth(api_client, user)
    resp = api_client.get(reverse("products-search"), {"q": "refri"})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["id"] == match.id
    assert data[0]["name"] == "Refrigerante Cola"
    assert set(data[0].keys()) == {"id", "name", "price"}


@pytest.mark.django_db
def test_products_search_by_alias(api_client):
    tenant = TenantFactory()
    user = UserFactory(tenant=tenant, email="prod-alias@example.com")
    ProductFactory(
        tenant=tenant,
        name="Biscoito",
        search_aliases="bolacha, cookie",
        status=Product.Status.ACTIVE,
    )
    _auth(api_client, user)
    resp = api_client.get(reverse("products-search"), {"q": "bolacha"})
    assert resp.status_code == 200
    assert len(resp.json()) == 1
    assert resp.json()[0]["name"] == "Biscoito"

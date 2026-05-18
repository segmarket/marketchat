import pytest
from django.urls import reverse
from rest_framework_simplejwt.tokens import RefreshToken

from apps.markets.models import Market
from tests.factories import MarketFactory, TenantFactory, UserFactory


def _auth(client, user):
    client.credentials(
        HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(user).access_token}"
    )


@pytest.mark.django_db
def test_markets_crud(api_client):
    tenant = TenantFactory()
    user = UserFactory(tenant=tenant, email="markets-crud@example.com")
    _auth(api_client, user)

    create_resp = api_client.post(
        reverse("markets-list"),
        {
            "name": "Condomínio Vista Alegre - Bloco B",
            "address": "Av. Principal, 100 — Campinas, SP",
            "status": "active",
        },
        format="json",
    )
    assert create_resp.status_code == 201
    market_id = create_resp.json()["id"]
    assert create_resp.json()["name"] == "Condomínio Vista Alegre - Bloco B"

    list_resp = api_client.get(reverse("markets-list"))
    assert list_resp.status_code == 200
    ids = [m["id"] for m in list_resp.json()]
    assert market_id in ids

    patch_resp = api_client.patch(
        reverse("markets-detail", kwargs={"pk": market_id}),
        {"name": "Vista Alegre Bloco B", "status": "inactive"},
        format="json",
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["name"] == "Vista Alegre Bloco B"
    assert patch_resp.json()["status"] == "inactive"

    put_resp = api_client.put(
        reverse("markets-detail", kwargs={"pk": market_id}),
        {
            "name": "Vista Alegre Atualizado",
            "address": "Nova Rua, 200",
            "status": "active",
        },
        format="json",
    )
    assert put_resp.status_code == 200
    assert put_resp.json()["address"] == "Nova Rua, 200"

    delete_resp = api_client.delete(reverse("markets-detail", kwargs={"pk": market_id}))
    assert delete_resp.status_code == 204

    list_after = api_client.get(reverse("markets-list"))
    assert market_id not in [m["id"] for m in list_after.json()]
    assert not Market.all_objects.filter(pk=market_id).exists()


@pytest.mark.django_db
def test_markets_list_filter_by_name_status_address(api_client):
    tenant = TenantFactory()
    user = UserFactory(tenant=tenant, email="markets-filter@example.com")
    MarketFactory(
        tenant=tenant,
        name="Condomínio Sol",
        address="Rua das Flores, 10 — Campinas",
        status=Market.Status.ACTIVE,
    )
    MarketFactory(
        tenant=tenant,
        name="Residencial Lua",
        address="Av. Brasil, 200 — São Paulo",
        status=Market.Status.INACTIVE,
    )

    _auth(api_client, user)
    by_name = api_client.get(reverse("markets-list"), {"name": "sol"})
    assert by_name.status_code == 200
    assert len(by_name.json()) == 1
    assert by_name.json()[0]["name"] == "Condomínio Sol"

    by_status = api_client.get(reverse("markets-list"), {"status": "inactive"})
    assert by_status.status_code == 200
    assert len(by_status.json()) == 1
    assert by_status.json()[0]["name"] == "Residencial Lua"

    by_address = api_client.get(reverse("markets-list"), {"address": "Campinas"})
    assert by_address.status_code == 200
    assert len(by_address.json()) == 1


@pytest.mark.django_db
def test_markets_create_rejects_empty_fields(api_client):
    tenant = TenantFactory()
    user = UserFactory(tenant=tenant, email="markets-val@example.com")
    _auth(api_client, user)

    resp_name = api_client.post(
        reverse("markets-list"),
        {"name": "   ", "address": "Rua Válida, 1"},
        format="json",
    )
    assert resp_name.status_code == 400

    resp_address = api_client.post(
        reverse("markets-list"),
        {"name": "Mercado OK", "address": ""},
        format="json",
    )
    assert resp_address.status_code == 400


@pytest.mark.django_db
def test_markets_tenant_isolation(api_client):
    tenant_a = TenantFactory()
    tenant_b = TenantFactory()
    user_a = UserFactory(tenant=tenant_a, email="markets-a@example.com")
    user_b = UserFactory(tenant=tenant_b, email="markets-b@example.com")

    market_a = MarketFactory(
        tenant=tenant_a,
        name="Mercado Tenant A",
        address="Endereço A",
    )

    _auth(api_client, user_b)
    list_resp = api_client.get(reverse("markets-list"))
    assert list_resp.status_code == 200
    assert market_a.id not in [m["id"] for m in list_resp.json()]

    patch_resp = api_client.patch(
        reverse("markets-detail", kwargs={"pk": market_a.id}),
        {"name": "Hack"},
        format="json",
    )
    assert patch_resp.status_code == 404

    put_resp = api_client.put(
        reverse("markets-detail", kwargs={"pk": market_a.id}),
        {"name": "Hack", "address": "X", "status": "active"},
        format="json",
    )
    assert put_resp.status_code == 404

    delete_resp = api_client.delete(reverse("markets-detail", kwargs={"pk": market_a.id}))
    assert delete_resp.status_code == 404

    assert Market.all_objects.filter(pk=market_a.id).exists()

    _auth(api_client, user_a)
    detail_resp = api_client.get(reverse("markets-detail", kwargs={"pk": market_a.id}))
    assert detail_resp.status_code == 200
    assert detail_resp.json()["name"] == "Mercado Tenant A"

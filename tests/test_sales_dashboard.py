from decimal import Decimal
from io import BytesIO

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.sales.models import Cart
from apps.sales.services.dashboard_metrics import compute_dashboard_metrics, DashboardFilters
from tests.factories import (
    CartFactory,
    CartItemFactory,
    MarketFactory,
    ProductFactory,
    ResidentFactory,
    TenantFactory,
    UserFactory,
)


def _auth(client, user):
    client.credentials(
        HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(user).access_token}",
    )


@pytest.mark.django_db
def test_metrics_only_count_completed_revenue():
    tenant = TenantFactory()
    market = MarketFactory(tenant=tenant)
    resident = ResidentFactory(tenant=tenant, market=market)

    CartFactory(
        tenant=tenant,
        resident=resident,
        status=Cart.Status.COMPLETED,
        total_value=Decimal("100.00"),
    )
    CartFactory(
        tenant=tenant,
        resident=resident,
        status=Cart.Status.COMPLETED,
        total_value=Decimal("50.00"),
    )
    CartFactory(
        tenant=tenant,
        resident=resident,
        status=Cart.Status.OPEN,
        total_value=Decimal("999.00"),
    )
    CartFactory(
        tenant=tenant,
        resident=resident,
        status=Cart.Status.CANCELLED,
        total_value=Decimal("40.00"),
    )

    metrics = compute_dashboard_metrics(DashboardFilters(tenant_id=tenant.id))
    assert metrics.total_revenue == Decimal("150.00")
    assert metrics.total_orders == 2
    assert metrics.average_ticket == Decimal("75.00")
    assert metrics.abandoned_orders == 1


@pytest.mark.django_db
def test_conversion_rate_with_funnel():
    tenant = TenantFactory()
    resident = ResidentFactory(tenant=tenant)

    CartFactory(tenant=tenant, resident=resident, status=Cart.Status.COMPLETED)
    CartFactory(tenant=tenant, resident=resident, status=Cart.Status.CANCELLED)
    CartFactory(tenant=tenant, resident=resident, status=Cart.Status.OPEN)

    metrics = compute_dashboard_metrics(DashboardFilters(tenant_id=tenant.id))
    assert metrics.total_orders == 1
    assert metrics.conversion_rate == round(1 / 3, 4)


@pytest.mark.django_db
def test_dashboard_api_tenant_isolation(api_client):
    tenant_a = TenantFactory()
    tenant_b = TenantFactory()
    user_a = UserFactory(tenant=tenant_a, email="sales-a@example.com")
    user_b = UserFactory(tenant=tenant_b, email="sales-b@example.com")

    resident_a = ResidentFactory(tenant=tenant_a)
    resident_b = ResidentFactory(tenant=tenant_b)
    cart_a = CartFactory(
        tenant=tenant_a,
        resident=resident_a,
        status=Cart.Status.COMPLETED,
        total_value=Decimal("10.00"),
    )
    CartFactory(
        tenant=tenant_b,
        resident=resident_b,
        status=Cart.Status.COMPLETED,
        total_value=Decimal("99.00"),
    )

    _auth(api_client, user_a)
    resp_a = api_client.get(reverse("sales-dashboard"))
    assert resp_a.status_code == 200
    assert resp_a.json()["metrics"]["total_revenue"] == "10.00"
    ids_a = [row["id"] for row in resp_a.json()["orders"]["results"]]
    assert cart_a.id in ids_a

    _auth(api_client, user_b)
    resp_b = api_client.get(reverse("sales-dashboard"))
    assert resp_b.json()["metrics"]["total_revenue"] == "99.00"


@pytest.mark.django_db
def test_dashboard_filters_status_and_resident_name(api_client):
    tenant = TenantFactory()
    user = UserFactory(tenant=tenant, email="sales-filter@example.com")
    market = MarketFactory(tenant=tenant, name="Condomínio Norte")

    ana = ResidentFactory(tenant=tenant, market=market, name="Ana Costa")
    bob = ResidentFactory(tenant=tenant, market=market, name="Bruno Lima")

    completed = CartFactory(
        tenant=tenant,
        resident=ana,
        status=Cart.Status.COMPLETED,
        total_value=Decimal("20.00"),
    )
    CartFactory(
        tenant=tenant,
        resident=bob,
        status=Cart.Status.AWAITING_PAYMENT,
        total_value=Decimal("30.00"),
    )

    _auth(api_client, user)
    by_name = api_client.get(
        reverse("sales-dashboard"),
        {"resident_name": "ana", "status": "COMPLETED"},
    )
    assert by_name.status_code == 200
    results = by_name.json()["orders"]["results"]
    assert len(results) == 1
    assert results[0]["id"] == completed.id
    assert results[0]["resident_name"] == "Ana Costa"


@pytest.mark.django_db
def test_cart_detail_with_photo_url(api_client):
    tenant = TenantFactory()
    user = UserFactory(tenant=tenant, email="sales-detail@example.com")
    market = MarketFactory(tenant=tenant)
    resident = ResidentFactory(tenant=tenant, market=market, name="Maria")
    product = ProductFactory(tenant=tenant, name="Água", sku="AGU-01")
    cart = CartFactory(
        tenant=tenant,
        resident=resident,
        status=Cart.Status.AWAITING_PAYMENT,
        total_value=Decimal("5.00"),
        asaas_billing_id="pay_123",
    )
    cart.product_photo.save(
        "foto.jpg",
        SimpleUploadedFile(
            "foto.jpg",
            BytesIO(b"fake-bytes").getvalue(),
            content_type="image/jpeg",
        ),
        save=True,
    )
    CartItemFactory(cart=cart, product=product, quantity=2, unit_price=Decimal("2.50"))

    _auth(api_client, user)
    resp = api_client.get(reverse("sales-cart-detail", kwargs={"pk": cart.id}))
    assert resp.status_code == 200
    body = resp.json()
    assert body["asaas_billing_id"] == "pay_123"
    assert body["security_photo_url"]
    assert len(body["items"]) == 1
    assert body["items"][0]["product_name"] == "Água"
    assert body["items"][0]["subtotal"] == "5.00"


@pytest.mark.django_db
def test_cart_detail_other_tenant_404(api_client):
    tenant_a = TenantFactory()
    tenant_b = TenantFactory()
    user_b = UserFactory(tenant=tenant_b, email="sales-iso@example.com")
    cart_a = CartFactory(tenant=tenant_a, resident=ResidentFactory(tenant=tenant_a))

    _auth(api_client, user_b)
    resp = api_client.get(reverse("sales-cart-detail", kwargs={"pk": cart_a.id}))
    assert resp.status_code == 404

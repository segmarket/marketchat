"""Provisiona o tenant fictício Portal + catálogo para a degustação da landing."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.integrations.models import WhatsappInstance
from apps.markets.models import Market
from apps.products.models import Product
from apps.tenants.models import Tenant

DEMO_TENANT_SLUG = "portal-demo"
DEMO_INSTANCE_NAME = "demo-portal-landing"
DEMO_API_KEY = "demo-no-evolution"

DEMO_PRODUCTS: tuple[tuple[str, str, str, str], ...] = (
    ("COCA-2L", "Coca-Cola 2L", "12.50", "coca, cocacola, coquinha"),
    ("COCA-LATA", "Coca-Cola Lata 350ml", "4.50", "coca, lata"),
    ("SUCRILHOS", "Sucrilhos 300g", "14.90", "sucrilhos, cereal"),
    ("CAFE", "Café Torrado 500g", "22.90", "cafe, café"),
    ("PAO", "Pão de Forma 500g", "9.90", "pao, pão, forma"),
    ("PEPSI", "Pepsi 350ml", "4.20", "pepsi, pesi"),
)


@dataclass(frozen=True)
class DemoPortalBundle:
    tenant: Tenant
    market: Market
    instance: WhatsappInstance


def get_demo_tenant_slug() -> str:
    return getattr(settings, "DEMO_TENANT_SLUG", DEMO_TENANT_SLUG) or DEMO_TENANT_SLUG


@transaction.atomic
def ensure_demo_portal() -> DemoPortalBundle:
    """Cria (se necessário) tenant Portal, mercado, instância stub e produtos demo."""
    slug = get_demo_tenant_slug()
    now = timezone.now()
    tenant, _ = Tenant.objects.get_or_create(
        slug=slug,
        defaults={
            "name": "Portal",
            "trial_started_at": now,
            "trial_ends_at": now + timedelta(days=3650),
            "subscription_status": Tenant.SubscriptionStatus.ACTIVE,
            "is_bot_active_global": True,
            "is_whatsapp_connected": True,
        },
    )
    # Garante flags mesmo se o tenant já existia
    updates: list[str] = []
    if not tenant.is_bot_active_global:
        tenant.is_bot_active_global = True
        updates.append("is_bot_active_global")
    if tenant.subscription_status == Tenant.SubscriptionStatus.SUSPENDED:
        tenant.subscription_status = Tenant.SubscriptionStatus.ACTIVE
        updates.append("subscription_status")
    if updates:
        updates.append("updated_at")
        tenant.save(update_fields=updates)

    market, _ = Market.objects.get_or_create(
        tenant=tenant,
        name="Portal",
        defaults={
            "address": "Condomínio Portal — Demonstração MarketChat",
            "status": Market.Status.ACTIVE,
        },
    )
    Market.objects.get_or_create(
        tenant=tenant,
        name="Aurora",
        defaults={
            "address": "Condomínio Aurora — Demonstração MarketChat",
            "status": Market.Status.ACTIVE,
        },
    )

    instance, _ = WhatsappInstance.objects.get_or_create(
        tenant=tenant,
        defaults={
            "instance_name": DEMO_INSTANCE_NAME,
            "instance_id": "demo-portal",
            "api_key": DEMO_API_KEY,
            "webhook_url": "",
            "webhook_secret": "demo",
            "connection_status": WhatsappInstance.ConnectionStatus.OPEN,
            "is_active": True,
        },
    )
    if instance.api_key != DEMO_API_KEY:
        instance.api_key = DEMO_API_KEY
        instance.is_active = True
        instance.connection_status = WhatsappInstance.ConnectionStatus.OPEN
        instance.save(
            update_fields=["api_key", "is_active", "connection_status", "updated_at"],
        )

    for sku, name, price, aliases in DEMO_PRODUCTS:
        Product.objects.update_or_create(
            tenant=tenant,
            sku=sku,
            defaults={
                "name": name,
                "price": Decimal(price),
                "status": Product.Status.ACTIVE,
                "search_aliases": aliases,
            },
        )

    return DemoPortalBundle(tenant=tenant, market=market, instance=instance)

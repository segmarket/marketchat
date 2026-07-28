"""Provisiona customer Asaas Consumidor Final para tenants existentes."""

from __future__ import annotations

from django.core.management.base import BaseCommand
from django.db.models import Exists, OuterRef

from apps.billing.services.tenant_default_asaas_customer import (
    TenantDefaultCustomerError,
    ensure_tenant_default_asaas_customer,
    tenant_has_valid_billing_document,
)
from apps.markets.models import Market
from apps.tenants.models import Tenant


class Command(BaseCommand):
    help = (
        "Cria customer Asaas Consumidor Final para tenants sem asaas_default_customer_id."
    )

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Lista tenants elegíveis sem chamar o Asaas.",
        )
        parser.add_argument(
            "--tenant-id",
            type=int,
            default=None,
            help="Processar apenas um tenant.",
        )
        parser.add_argument(
            "--all-tenants",
            action="store_true",
            help="Incluir tenants sem mercado cadastrado.",
        )

    def handle(self, *args, **options) -> None:
        dry_run: bool = options["dry_run"]
        tenant_id: int | None = options["tenant_id"]
        require_market = not options["all_tenants"]

        qs = Tenant.objects.all().order_by("id")
        if tenant_id is not None:
            qs = qs.filter(pk=tenant_id)
        qs = qs.filter(asaas_default_customer_id="")

        if require_market:
            has_market = Market.all_objects.filter(tenant_id=OuterRef("pk"))
            qs = qs.annotate(_has_market=Exists(has_market)).filter(_has_market=True)

        ok = skip = err = 0
        for tenant in qs:
            if not tenant_has_valid_billing_document(tenant):
                self.stdout.write(
                    self.style.WARNING(
                        f"skip tenant={tenant.pk} ({tenant.name}): sem CPF/CNPJ válido",
                    ),
                )
                skip += 1
                continue

            if dry_run:
                self.stdout.write(
                    f"dry-run tenant={tenant.pk} ({tenant.name}) → criaria Consumidor Final",
                )
                ok += 1
                continue

            try:
                customer_id = ensure_tenant_default_asaas_customer(tenant)
                self.stdout.write(
                    self.style.SUCCESS(
                        f"ok tenant={tenant.pk} customer={customer_id}",
                    ),
                )
                ok += 1
            except TenantDefaultCustomerError as exc:
                self.stdout.write(
                    self.style.ERROR(f"erro tenant={tenant.pk}: {exc}"),
                )
                err += 1

        self.stdout.write(f"Resumo: ok={ok} skip={skip} erro={err}")

"""Confirmação atômica da importação de produtos."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from apps.products.models import Product, ProductImportSession


class ImportApplyError(ValueError):
    pass


@dataclass
class ApplyResult:
    created: int
    updated: int


def confirm_import(session: ProductImportSession) -> ApplyResult:
    if session.confirmed_at is not None:
        raise ImportApplyError("Esta importação já foi confirmada.")
    if session.expires_at <= timezone.now():
        raise ImportApplyError("O token de importação expirou. Faça o preview novamente.")

    to_create: list[Product] = []
    to_update: list[Product] = []

    for op in session.payload:
        price = Decimal(op["price"]).quantize(Decimal("0.01"))
        if op["action"] == "create":
            to_create.append(
                Product(
                    tenant_id=session.tenant_id,
                    sku=op["sku"],
                    name=op["name"],
                    search_aliases=(op.get("search_aliases") or "").strip(),
                    price=price,
                    status=op["status"],
                )
            )
        elif op["action"] == "update":
            to_update.append(
                Product(
                    id=op["product_id"],
                    tenant_id=session.tenant_id,
                    sku=op["sku"],
                    name=op["name"],
                    search_aliases=(op.get("search_aliases") or "").strip(),
                    price=price,
                    status=op["status"],
                )
            )

    now = timezone.now()
    for product in to_update:
        product.updated_at = now

    with transaction.atomic():
        if to_create:
            Product.all_objects.bulk_create(to_create)
        if to_update:
            Product.all_objects.bulk_update(
                to_update,
                fields=["name", "search_aliases", "price", "status", "updated_at"],
            )
        session.confirmed_at = timezone.now()
        session.save(update_fields=["confirmed_at"])

    return ApplyResult(created=len(to_create), updated=len(to_update))

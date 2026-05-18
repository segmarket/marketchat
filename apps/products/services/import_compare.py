"""Comparação de planilha com produtos existentes por SKU."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from apps.products.models import Product


@dataclass
class PreviewResult:
    operations: list[dict[str, Any]]
    new_count: int
    updated_count: int


def _row_differs(existing: Product, row: dict[str, Any]) -> bool:
    price = Decimal(row["price"]).quantize(Decimal("0.01"))
    return (
        existing.name != row["name"]
        or existing.price != price
        or existing.status != row["status"]
    )


def build_import_preview(tenant_id: int, rows: list[dict[str, Any]]) -> PreviewResult:
    existing_by_sku = {
        p.sku: p
        for p in Product.all_objects.filter(tenant_id=tenant_id).only(
            "id", "sku", "name", "price", "status"
        )
    }

    operations: list[dict[str, Any]] = []
    new_count = 0
    updated_count = 0

    for row in rows:
        sku = row["sku"]
        existing = existing_by_sku.get(sku)
        if existing is None:
            operations.append({**row, "action": "create"})
            new_count += 1
            continue
        if _row_differs(existing, row):
            operations.append(
                {
                    **row,
                    "action": "update",
                    "product_id": existing.id,
                }
            )
            updated_count += 1

    return PreviewResult(
        operations=operations,
        new_count=new_count,
        updated_count=updated_count,
    )

"""Busca de produtos no catálogo (palavras independentes da ordem)."""

from __future__ import annotations

from django.db.models import Q

from apps.products.models import Product

PRODUCT_TERM_NONE = "NONE"

ASK_PRODUCT_MESSAGE = (
    "Excelente! O que você deseja comprar? Me diga o nome do produto ou marca "
    "(ex: Coca-Cola, Doritos, Chocolate)."
)


def normalize_extracted_term(term: str) -> str:
    """Remove aspas e espaços extras do retorno da IA."""
    cleaned = (term or "").strip().strip("\"'“”‘’")
    return " ".join(cleaned.split())


def is_product_term_none(term: str) -> bool:
    return normalize_extracted_term(term).upper() == PRODUCT_TERM_NONE


def build_product_name_q(term: str) -> Q:
    """
    Cada palavra do termo deve aparecer no nome (ordem livre).
    Ex.: "Coca Zero" encontra "Coca Cola Lata Zero 350ml".
    """
    words = [w for w in normalize_extracted_term(term).split() if len(w) > 1]
    if not words:
        return Q(pk__in=[])
    query = Q()
    for word in words:
        query &= Q(name__icontains=word)
    return query


def search_active_products(
    tenant_id: int,
    term: str,
    *,
    limit: int = 10,
) -> list[Product]:
    if is_product_term_none(term):
        return []
    name_filter = build_product_name_q(term)
    return list(
        Product.objects.filter(
            tenant_id=tenant_id,
            status=Product.Status.ACTIVE,
        )
        .filter(name_filter)
        .order_by("name")[:limit],
    )

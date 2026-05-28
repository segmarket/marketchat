"""Busca de produtos no catálogo (palavras independentes da ordem + fuzzy)."""

from __future__ import annotations

import re
import unicodedata
from difflib import SequenceMatcher

from django.conf import settings
from django.db.models import Q

from apps.products.models import Product

PRODUCT_TERM_NONE = "NONE"

ASK_PRODUCT_MESSAGE = (
    "Excelente! O que você deseja comprar? Me diga o nome do produto ou marca "
    "(ex: Coca-Cola, Doritos, Chocolate)."
)

MAIN_MENU_PURCHASE_PROMPT = (
    "Excelente! Digite o nome do produto que deseja buscar."
)


def normalize_extracted_term(term: str) -> str:
    """Remove aspas e espaços extras do retorno da IA."""
    cleaned = (term or "").strip().strip("\"'“”‘’")
    return " ".join(cleaned.split())


def is_product_term_none(term: str) -> bool:
    return normalize_extracted_term(term).upper() == PRODUCT_TERM_NONE


def _normalize_for_match(text: str) -> str:
    lowered = (text or "").strip().lower()
    decomposed = unicodedata.normalize("NFD", lowered)
    return "".join(c for c in decomposed if unicodedata.category(c) != "Mn")


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


def _fuzzy_threshold() -> float:
    return float(getattr(settings, "PRODUCT_FUZZY_MATCH_THRESHOLD", 0.65))


def _product_search_corpus(product: Product) -> str:
    parts = [product.name or ""]
    aliases = (product.search_aliases or "").strip()
    if aliases:
        parts.append(aliases.replace(",", " ").replace("\n", " "))
    return _normalize_for_match(" ".join(parts))


def _similarity(left: str, right: str) -> float:
    if not left or not right:
        return 0.0
    return SequenceMatcher(None, left, right).ratio()


def _score_product_match(term: str, product: Product) -> float:
    corpus = _product_search_corpus(product)
    if not corpus:
        return 0.0

    scores = [_similarity(term, corpus)]
    words = [w for w in term.split() if len(w) > 2]
    for word in words:
        scores.append(_similarity(word, corpus))
        for token in re.findall(r"[a-z0-9]+", corpus):
            if len(token) > 2:
                scores.append(_similarity(word, token))
    return max(scores)


MIN_FUZZY_TERM_LENGTH = 4


def fuzzy_search_active_products(
    tenant_id: int,
    term: str,
    *,
    limit: int = 10,
    threshold: float | None = None,
) -> list[Product]:
    """Fallback quando icontains não encontra (typos)."""
    normalized_term = _normalize_for_match(normalize_extracted_term(term))
    if not normalized_term or is_product_term_none(term):
        return []
    if len(normalized_term.replace(" ", "")) < MIN_FUZZY_TERM_LENGTH:
        return []

    min_score = threshold if threshold is not None else _fuzzy_threshold()
    candidates = Product.objects.filter(
        tenant_id=tenant_id,
        status=Product.Status.ACTIVE,
    ).only("id", "name", "search_aliases", "sku", "price", "status", "tenant_id")

    scored: list[tuple[float, Product]] = []
    for product in candidates:
        score = _score_product_match(normalized_term, product)
        if score >= min_score:
            scored.append((score, product))

    scored.sort(key=lambda item: (-item[0], item[1].name))
    return [product for _, product in scored[:limit]]


def search_active_products(
    tenant_id: int,
    term: str,
    *,
    limit: int = 10,
) -> list[Product]:
    if is_product_term_none(term):
        return []
    name_filter = build_product_name_q(term)
    results = list(
        Product.objects.filter(
            tenant_id=tenant_id,
            status=Product.Status.ACTIVE,
        )
        .filter(name_filter)
        .order_by("name")[:limit],
    )
    if results:
        return results
    return fuzzy_search_active_products(tenant_id, term, limit=limit)

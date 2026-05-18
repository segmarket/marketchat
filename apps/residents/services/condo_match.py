from __future__ import annotations

import difflib
import unicodedata

from django.conf import settings

from apps.markets.models import Market


def _normalize_query(value: str) -> str:
    text = (value or "").strip().lower()
    text = unicodedata.normalize("NFKD", text)
    return "".join(c for c in text if not unicodedata.combining(c))


def find_market_by_query(tenant_id: int, query: str) -> Market | None:
    """Busca mercado ativo por correspondência textual ou fuzzy."""
    normalized = _normalize_query(query)
    if not normalized:
        return None

    markets = list(
        Market.all_objects.filter(
            tenant_id=tenant_id,
            status=Market.Status.ACTIVE,
        ).order_by("name")
    )
    if not markets:
        return None

    for market in markets:
        if normalized in _normalize_query(market.name):
            return market

    min_ratio = float(getattr(settings, "RESIDENT_CONDO_MATCH_MIN_RATIO", 0.55))
    best: Market | None = None
    best_score = 0.0
    for market in markets:
        score = difflib.SequenceMatcher(
            None,
            normalized,
            _normalize_query(market.name),
        ).ratio()
        if score > best_score:
            best_score = score
            best = market

    if best is not None and best_score >= min_ratio:
        return best
    return None

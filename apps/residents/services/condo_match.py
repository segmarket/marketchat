"""Match de condomínio (Market) no onboarding WhatsApp."""

from __future__ import annotations

import difflib
import logging
import unicodedata

from django.conf import settings
from django.db import connection
from django.db.utils import ProgrammingError

from apps.markets.models import Market

logger = logging.getLogger(__name__)


def _normalize_query(value: str) -> str:
    text = (value or "").strip().lower()
    text = unicodedata.normalize("NFKD", text)
    return "".join(c for c in text if not unicodedata.combining(c))


def _pg_trgm_available() -> bool:
    if connection.vendor != "postgresql":
        return False
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1 FROM pg_extension WHERE extname = 'pg_trgm'")
        return cursor.fetchone() is not None


def _find_market_trigram(tenant_id: int, query: str) -> Market | None:
    """Busca fuzzy no Postgres (pg_trgm), sempre filtrada pelo tenant."""
    from django.contrib.postgres.search import TrigramWordSimilarity

    text = (query or "").strip()
    if not text:
        return None

    min_similarity = float(
        getattr(settings, "RESIDENT_CONDO_TRIGRAM_MIN_SIMILARITY", 0.3)
    )
    return (
        Market.all_objects.filter(
            tenant_id=tenant_id,
            status=Market.Status.ACTIVE,
        )
        .annotate(similaridade=TrigramWordSimilarity(text, "name"))
        .filter(similaridade__gt=min_similarity)
        .order_by("-similaridade")
        .first()
    )


def _find_market_fallback(tenant_id: int, query: str) -> Market | None:
    """Fallback: substring (nome na frase) + difflib."""
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

    # Frase longa contendo o nome do condomínio (caso típico do WhatsApp).
    for market in markets:
        market_norm = _normalize_query(market.name)
        if not market_norm:
            continue
        if market_norm in normalized or normalized in market_norm:
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


def find_market_by_query(tenant_id: int, query: str) -> Market | None:
    """Busca mercado ativo do tenant por similaridade (trigram no Postgres)."""
    if not (query or "").strip():
        return None
    if connection.vendor == "postgresql" and _pg_trgm_available():
        try:
            return _find_market_trigram(tenant_id, query)
        except ProgrammingError:
            logger.warning(
                "Trigram condo match falhou; usando fallback difflib.",
                exc_info=True,
            )
    return _find_market_fallback(tenant_id, query)

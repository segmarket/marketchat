"""Match de condomínio (Market) no onboarding WhatsApp."""

from __future__ import annotations

import difflib
import logging
import unicodedata
from dataclasses import dataclass, field
from typing import Literal

from django.conf import settings
from django.db import connection
from django.db.utils import ProgrammingError

from apps.markets.models import Market

logger = logging.getLogger(__name__)

CondoMatchKind = Literal["perfect", "suggestions", "list_all", "none"]

LIST_ALL_LIMIT_DEFAULT = 15


@dataclass
class CondoMatchResult:
    kind: CondoMatchKind
    market: Market | None = None
    suggestions: list[tuple[Market, float]] = field(default_factory=list)


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


def _perfect_threshold() -> float:
    return float(getattr(settings, "RESIDENT_CONDO_PERFECT_SIMILARITY", 0.7))


def _min_similarity() -> float:
    return float(getattr(settings, "RESIDENT_CONDO_TRIGRAM_MIN_SIMILARITY", 0.3))


def _list_all_limit() -> int:
    return int(
        getattr(settings, "RESIDENT_CONDO_LIST_ALL_LIMIT", LIST_ALL_LIMIT_DEFAULT)
    )


def _list_all_active_markets(tenant_id: int) -> CondoMatchResult:
    """Fallback amigável: lista mercados ativos do tenant (cap para WhatsApp)."""
    markets = list(
        Market.all_objects.filter(
            tenant_id=tenant_id,
            status=Market.Status.ACTIVE,
        ).order_by("name")[: _list_all_limit()]
    )
    if not markets:
        return CondoMatchResult(kind="none")
    return CondoMatchResult(
        kind="list_all",
        suggestions=[(market, 0.0) for market in markets],
    )


def _result_from_scored(
    scored: list[tuple[Market, float]],
    *,
    tenant_id: int,
) -> CondoMatchResult:
    """Aplica limiares: > perfect → auto; >= min e <= perfect → sugestões; senão list_all."""
    if not scored:
        return _list_all_active_markets(tenant_id)

    scored = sorted(scored, key=lambda item: item[1], reverse=True)
    top_market, top_score = scored[0]
    perfect = _perfect_threshold()
    minimum = _min_similarity()

    if top_score > perfect:
        return CondoMatchResult(kind="perfect", market=top_market)

    medium = [
        (market, score)
        for market, score in scored
        if minimum <= score <= perfect
    ][:3]
    if medium:
        return CondoMatchResult(kind="suggestions", suggestions=medium)

    return _list_all_active_markets(tenant_id)


def _find_market_trigram(tenant_id: int, query: str) -> CondoMatchResult:
    """Busca fuzzy no Postgres (pg_trgm), sempre filtrada pelo tenant."""
    from django.contrib.postgres.search import TrigramWordSimilarity

    text = (query or "").strip()
    if not text:
        return CondoMatchResult(kind="none")

    minimum = _min_similarity()
    qs = (
        Market.all_objects.filter(
            tenant_id=tenant_id,
            status=Market.Status.ACTIVE,
        )
        .annotate(similaridade=TrigramWordSimilarity(text, "name"))
        .filter(similaridade__gte=minimum)
        .order_by("-similaridade")[:3]
    )
    scored = [(row, float(row.similaridade)) for row in qs]
    return _result_from_scored(scored, tenant_id=tenant_id)


def _find_market_fallback(tenant_id: int, query: str) -> CondoMatchResult:
    """Fallback: substring (nome na frase) + difflib com os mesmos tiers."""
    normalized = _normalize_query(query)
    if not normalized:
        return CondoMatchResult(kind="none")

    markets = list(
        Market.all_objects.filter(
            tenant_id=tenant_id,
            status=Market.Status.ACTIVE,
        ).order_by("name")
    )
    if not markets:
        return CondoMatchResult(kind="none")

    # Frase longa contendo o nome do condomínio (caso típico do WhatsApp).
    for market in markets:
        market_norm = _normalize_query(market.name)
        if not market_norm:
            continue
        if market_norm in normalized or normalized in market_norm:
            return CondoMatchResult(kind="perfect", market=market)

    scored: list[tuple[Market, float]] = []
    for market in markets:
        score = difflib.SequenceMatcher(
            None,
            normalized,
            _normalize_query(market.name),
        ).ratio()
        scored.append((market, score))

    return _result_from_scored(scored, tenant_id=tenant_id)


def match_markets_by_query(tenant_id: int, query: str) -> CondoMatchResult:
    """Busca mercados ativos: perfect / suggestions / list_all / none."""
    if not (query or "").strip():
        return CondoMatchResult(kind="none")
    if connection.vendor == "postgresql" and _pg_trgm_available():
        try:
            return _find_market_trigram(tenant_id, query)
        except ProgrammingError:
            logger.warning(
                "Trigram condo match falhou; usando fallback difflib.",
                exc_info=True,
            )
    return _find_market_fallback(tenant_id, query)


def find_market_by_query(tenant_id: int, query: str) -> Market | None:
    """Compat: retorna Market apenas em match perfeito."""
    result = match_markets_by_query(tenant_id, query)
    if result.kind == "perfect":
        return result.market
    return None

"""Triagem de intenção (gatekeeper) antes do fluxo de compra."""

from __future__ import annotations

import logging
import re

from apps.chatbot.services.chatbot_core import classify_gatekeeper_intent as _classify_gatekeeper

logger = logging.getLogger(__name__)

MAINTENANCE_ISSUE = "MAINTENANCE_ISSUE"
PAYMENT_ERROR = "PAYMENT_ERROR"
PURCHASE = "PURCHASE"
STOCK_ISSUE = "STOCK_ISSUE"
GENERAL = "GENERAL"

ALL_INTENTS = (
    MAINTENANCE_ISSUE,
    PAYMENT_ERROR,
    PURCHASE,
    STOCK_ISSUE,
    GENERAL,
)

# Relato de falta tem prioridade sobre "queria comprar" na mesma frase.
_STOCK_SHORTAGE_PATTERNS = (
    r"\bem falta\b",
    r"\best[aá] em falta\b",
    r"\bt[aá] em falta\b",
    r"\bsem estoque\b",
    r"\besgotad[oa]\b",
    r"\bacabou\b",
    r"\bn[aã]o tem\b",
    r"\bn[aã]o achei\b",
    r"\bn[aã]o encontrei\b",
    r"\bt[aá] vazi[oa]\b",
    r"\best[aá] vazi[oa]\b",
    r"\bgeladeira vazia\b",
    r"\bg[oô]ndola vazia\b",
    r"\bfreezer.*vazi",
    r"\bquando vai chegar\b",
    r"\bquando chega\b",
)


def _detect_stock_issue_heuristic(message: str) -> bool:
    """Fallback local: compra + falta na mesma mensagem → STOCK_ISSUE."""
    text = (message or "").strip().lower()
    if not text:
        return False
    return any(re.search(pattern, text) for pattern in _STOCK_SHORTAGE_PATTERNS)


def classify_user_intent(message: str) -> str:
    """
    Classifica a mensagem do morador antes de qualquer busca no catálogo.
    Texto puro (sem JSON). Em falha, retorna GENERAL.
    """
    stripped = (message or "").strip()
    if not stripped:
        return GENERAL

    if _detect_stock_issue_heuristic(stripped):
        logger.info("Gatekeeper heurístico: STOCK_ISSUE para %r", stripped[:80])
        return STOCK_ISSUE

    tag = _classify_gatekeeper(stripped).strip().upper()
    if tag in ALL_INTENTS:
        return tag
    logger.warning("Gatekeeper: tag inesperada %r; usando GENERAL", tag)
    return GENERAL

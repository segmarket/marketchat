"""Triagem de intenção (gatekeeper) antes do fluxo de compra."""

from __future__ import annotations

import logging
import re
import unicodedata

from apps.chatbot.services.chatbot_core import classify_gatekeeper_intent as _classify_gatekeeper_core

logger = logging.getLogger(__name__)

MAINTENANCE_ISSUE = "MAINTENANCE_ISSUE"
COMPLAINT = "COMPLAINT"
PAYMENT_ERROR = "PAYMENT_ERROR"
PURCHASE = "PURCHASE"
STOCK_ISSUE = "STOCK_ISSUE"
COURTESY_FAREWELL = "COURTESY_FAREWELL"
GREETING = "GREETING"
GENERAL = "GENERAL"

ALL_INTENTS = (
    MAINTENANCE_ISSUE,
    COMPLAINT,
    PAYMENT_ERROR,
    PURCHASE,
    STOCK_ISSUE,
    GREETING,
    COURTESY_FAREWELL,
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

_COMPLAINT_PATTERNS = (
    r"\breclama",
    r"\breclam",
    r"\binsatisfeit",
    r"\bn[aã]o gostei\b",
    r"\batendimento (foi |est[aá] )?(p[eé]ssim|ruim|horr[ií]vel)",
    r"\bden[uú]ncia",
    r"\bproduto (estragado|vencido|estragad)",
)

_BARE_PRODUCT_MAX_WORDS = 4

_NON_PRODUCT_QUERY_PATTERNS = (
    r"\bpix\b",
    r"\bpag(a|ar|amento)\b",
    r"\breclam",
    r"\bqueimou\b",
    r"\bmaquininha\b",
    r"\bl[aâ]mpada\b",
    r"\bgeladeira\b",
    r"\bproblema\b",
    r"\bcancelar\b",
)

_OPENING_GREETING_EXACT = frozenset(
    {
        "oi",
        "ola",
        "olá",
        "opa",
        "eae",
        "e ae",
        "eai",
        "fala",
        "bom dia",
        "boa tarde",
        "boa noite",
        "salve",
    }
)

_OPENING_GREETING_PREFIXES = (
    "bom dia",
    "boa tarde",
    "boa noite",
    "oi",
    "ola",
    "olá",
    "opa",
    "eae",
    "e ae",
)

_GREETING_MAX_WORDS = 5

_COURTESY_MAX_WORDS = 6

_COURTESY_ROOTS = (
    "obrigad",
    "valeu",
    "brigad",
    "tchau",
    "ate logo",
    "até logo",
    "flw",
    "falou",
)

_COURTESY_ACK_WORDS = frozenset(
    {
        "certo",
        "ok",
        "okay",
        "show",
        "beleza",
        "blz",
        "perfeito",
        "entendi",
        "ta",
        "tá",
    }
)

_PURCHASE_SIGNAL_PATTERNS = (
    r"\bquero\b",
    r"\bcomprar\b",
    r"\blevar\b",
    r"\bpegar\b",
    r"\bmanda\b",
    r"\bpix\b",
)


def _normalize_text(text: str) -> str:
    lowered = (text or "").strip().lower()
    decomposed = unicodedata.normalize("NFD", lowered)
    return "".join(c for c in decomposed if unicodedata.category(c) != "Mn")


def _detect_complaint_heuristic(message: str) -> bool:
    text = (message or "").strip().lower()
    if not text:
        return False
    return any(re.search(pattern, text) for pattern in _COMPLAINT_PATTERNS)


def _detect_stock_issue_heuristic(message: str) -> bool:
    """Fallback local: compra + falta na mesma mensagem → STOCK_ISSUE."""
    text = (message or "").strip().lower()
    if not text:
        return False
    return any(re.search(pattern, text) for pattern in _STOCK_SHORTAGE_PATTERNS)


def _looks_like_bare_product_query(message: str) -> bool:
    """Nome de produto ou pergunta curta de disponibilidade → compra, sem chamar a IA."""
    text = (message or "").strip()
    if not text:
        return False
    lower = _normalize_text(text)
    if lower in _OPENING_GREETING_EXACT:
        return False
    words = text.split()
    if not 1 <= len(words) <= _BARE_PRODUCT_MAX_WORDS:
        return False
    if any(re.search(pattern, lower) for pattern in _NON_PRODUCT_QUERY_PATTERNS):
        return False
    return True


def _detect_greeting_heuristic(message: str) -> bool:
    """Saudação de abertura (não confundir com despedida/agradecimento)."""
    text = (message or "").strip()
    if not text:
        return False
    normalized = re.sub(r"[^\w\s]", "", _normalize_text(text)).strip()
    if not normalized:
        return False
    words = normalized.split()
    if len(words) > _GREETING_MAX_WORDS:
        return False
    if normalized in _OPENING_GREETING_EXACT:
        return True
    if len(words) <= 4 and any(
        normalized == prefix or normalized.startswith(f"{prefix} ")
        for prefix in _OPENING_GREETING_PREFIXES
    ):
        return True
    return False


def _detect_courtesy_heuristic(message: str) -> bool:
    """Agradecimento/despedida curta sem sinal de compra."""
    text = (message or "").strip()
    if not text:
        return False
    if _detect_greeting_heuristic(text):
        return False
    normalized = _normalize_text(text)
    words = text.split()
    if len(words) > _COURTESY_MAX_WORDS:
        return False
    if any(re.search(pattern, normalized) for pattern in _PURCHASE_SIGNAL_PATTERNS):
        return False
    if any(root in normalized for root in _COURTESY_ROOTS):
        return True
    if len(words) <= 3 and any(w in normalized.split() for w in _COURTESY_ACK_WORDS):
        if any(root in normalized for root in _COURTESY_ROOTS):
            return True
        if words[0].lower() in _COURTESY_ACK_WORDS and len(words) <= 2:
            return "obrigad" in normalized or "valeu" in normalized
    if len(words) <= 3:
        tokens = set(normalized.split())
        if tokens & _COURTESY_ACK_WORDS and (
            "obrigad" in normalized or "valeu" in normalized
        ):
            return True
    return False


def classify_user_intent(
    message: str,
    *,
    tenant_id: int | None = None,
    phone: str | None = None,
) -> str:
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

    if _detect_complaint_heuristic(stripped):
        logger.info("Gatekeeper heurístico: COMPLAINT para %r", stripped[:80])
        return COMPLAINT

    if _detect_greeting_heuristic(stripped):
        logger.info("Gatekeeper heurístico: GREETING para %r", stripped[:80])
        return GREETING

    if _detect_courtesy_heuristic(stripped):
        logger.info("Gatekeeper heurístico: COURTESY_FAREWELL para %r", stripped[:80])
        return COURTESY_FAREWELL

    if _looks_like_bare_product_query(stripped):
        logger.info("Gatekeeper heurístico: PURCHASE (produto solto) para %r", stripped[:80])
        return PURCHASE

    if tenant_id is not None and phone:
        from apps.chatbot.services.intent_classifier import classify_gatekeeper_intent

        tag = classify_gatekeeper_intent(
            message=stripped,
            tenant_id=tenant_id,
            phone=phone,
        ).strip().upper()
    else:
        tag = _classify_gatekeeper_core(stripped).strip().upper()

    if tag in ALL_INTENTS:
        return tag
    logger.warning("Gatekeeper: tag inesperada %r; usando GENERAL", tag)
    return GENERAL

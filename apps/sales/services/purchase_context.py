"""Contexto de compra: frases de intenção e disponibilidade."""

from __future__ import annotations

import re

PURCHASE_WITHOUT_PRODUCT_PHRASES = (
    "quero comprar",
    "vou comprar",
    "quero levar",
    "vou levar",
    "quero pegar",
    "vou pegar",
    "quero esse",
    "vou querer",
    "fechar compra",
    "como mando o pix",
    "mandar o pix",
    "mando o pix",
    "pagar no pix",
    "pagar pelo pix",
    "fechar no pix",
    "fazer o pix",
    "gerar o pix",
)

AVAILABILITY_PATTERNS = (
    r"\btem\b",
    r"\btêm\b",
    r"\bvoce[s]?\s+tem\b",
    r"\bvocês\s+tem\b",
    r"\bha\b",
    r"\bhá\b",
    r"\btem\s+dispon[ií]vel\b",
    r"\bvendem\b",
    r"\bvoc[eê]s\s+vendem\b",
)


def is_purchase_without_product(text: str) -> bool:
    normalized = (text or "").lower().strip()
    if not normalized:
        return False
    return any(phrase in normalized for phrase in PURCHASE_WITHOUT_PRODUCT_PHRASES)


def looks_like_availability_question(text: str) -> bool:
    normalized = (text or "").lower().strip()
    if not normalized:
        return False
    if is_purchase_without_product(normalized):
        return False
    return any(re.search(pattern, normalized) for pattern in AVAILABILITY_PATTERNS)

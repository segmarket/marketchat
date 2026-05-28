"""Escape e validação na escolha numerada de produtos (lista em texto)."""

from __future__ import annotations

import unicodedata

from apps.sales.services.cart_escape import is_global_escape_message

PRODUCT_SELECTION_ESCAPE_REPLY = (
    "Sem problemas! Vamos tentar de novo. Me diga o nome do produto de forma "
    "um pouco diferente, ou qual outro item você está procurando."
)

PRODUCT_SELECTION_INVALID_REPLY = (
    "Por favor, digite apenas o número correspondente ao produto na lista acima, "
    "ou digite 'nenhum' para buscar outra coisa."
)

_PRODUCT_SELECTION_ESCAPE_SUBSTRINGS = (
    "nao e esse",
    "nao eh esse",
    "não é esse",
    "nao e esse produto",
    "nao quero esse",
    "nao quero",
    "nenhum",
    "nenhuma",
    "errado",
    "errei",
    "outro produto",
    "outro item",
    "voltar",
    "cancela",
    "cancelar",
    "incorreto",
    "diferente",
)

_PRODUCT_SELECTION_ESCAPE_TOKENS = frozenset(
    {
        "nenhum",
        "nenhuma",
        "errado",
        "errei",
        "cancela",
        "voltar",
        "outro",
    },
)


def _normalize_selection_text(text: str) -> str:
    lowered = (text or "").strip().lower()
    decomposed = unicodedata.normalize("NFD", lowered)
    return "".join(c for c in decomposed if unicodedata.category(c) != "Mn")


def is_product_selection_escape(text: str) -> bool:
    """True se o morador rejeita a lista atual (não é escolha numérica)."""
    if is_global_escape_message(text):
        return True
    normalized = _normalize_selection_text(text)
    if not normalized:
        return False
    for phrase in _PRODUCT_SELECTION_ESCAPE_SUBSTRINGS:
        if phrase in normalized:
            return True
    tokens = set(normalized.split())
    if tokens & _PRODUCT_SELECTION_ESCAPE_TOKENS:
        return True
    if "nao" in normalized and any(
        fragment in normalized for fragment in ("esse", "esta", "esta lista")
    ):
        return True
    return False


def is_likely_new_product_search_text(text: str) -> bool:
    """Texto longo o suficiente para tratar como nova busca em vez de erro de digitação."""
    stripped = (text or "").strip()
    if len(stripped) < 3:
        return False
    return any(char.isalpha() for char in stripped)

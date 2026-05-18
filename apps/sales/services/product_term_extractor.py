"""Extração de termo de produto via OpenAI (gasto mínimo de tokens)."""

from __future__ import annotations

from apps.chatbot.services.chatbot_core import ChatbotCoreError, extract_product_term as _extract

ProductTermExtractorError = ChatbotCoreError


def extract_product_term(message: str) -> str:
    return _extract(message)

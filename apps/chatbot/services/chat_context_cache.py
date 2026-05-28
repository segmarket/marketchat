"""Memória de curto prazo do chat (Redis via Django cache) para o gatekeeper."""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)

_CACHE_KEY_PREFIX = "chat_context"
_VALID_ROLES = frozenset({"user", "assistant"})


def _phone_digits(phone: str) -> str:
    return re.sub(r"\D", "", phone or "")


def _cache_key(tenant_id: int, phone: str) -> str:
    digits = _phone_digits(phone)
    return f"{_CACHE_KEY_PREFIX}:{tenant_id}:{digits}"


def _max_messages() -> int:
    return int(getattr(settings, "CHAT_CONTEXT_MAX_MESSAGES", 4))


def _ttl_seconds() -> int:
    return int(getattr(settings, "CHAT_CONTEXT_TTL_SECONDS", 1200))


def get_recent_messages(tenant_id: int, phone: str) -> list[dict[str, str]]:
    """Últimas mensagens user/assistant (até CHAT_CONTEXT_MAX_MESSAGES)."""
    key = _cache_key(tenant_id, phone)
    if not _phone_digits(phone):
        return []
    try:
        raw = cache.get(key)
    except Exception:
        logger.warning(
            "chat_context: falha ao ler Redis tenant=%s phone=%s",
            tenant_id,
            _phone_digits(phone)[:6],
            exc_info=True,
        )
        return []
    if not raw:
        return []
    try:
        if isinstance(raw, str):
            data = json.loads(raw)
        elif isinstance(raw, list):
            data = raw
        else:
            return []
    except (json.JSONDecodeError, TypeError):
        logger.warning("chat_context: payload inválido em %s", key)
        return []

    result: list[dict[str, str]] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        role = str(item.get("role") or "").strip().lower()
        content = str(item.get("content") or "").strip()
        if role in _VALID_ROLES and content:
            result.append({"role": role, "content": content})
    return result[-_max_messages() :]


def append_message(
    tenant_id: int,
    phone: str,
    *,
    role: str,
    content: str,
) -> None:
    """Acrescenta mensagem ao buffer FIFO e renova TTL."""
    normalized_role = (role or "").strip().lower()
    text = (content or "").strip()
    if normalized_role not in _VALID_ROLES or not text or not _phone_digits(phone):
        return

    key = _cache_key(tenant_id, phone)
    try:
        history = get_recent_messages(tenant_id, phone)
        history.append({"role": normalized_role, "content": text})
        history = history[-_max_messages() :]
        cache.set(key, json.dumps(history, ensure_ascii=False), timeout=_ttl_seconds())
    except Exception:
        logger.warning(
            "chat_context: falha ao gravar Redis tenant=%s phone=%s",
            tenant_id,
            _phone_digits(phone)[:6],
            exc_info=True,
        )


def clear_context(tenant_id: int, phone: str) -> None:
    """Remove histórico (útil em testes)."""
    if not _phone_digits(phone):
        return
    try:
        cache.delete(_cache_key(tenant_id, phone))
    except Exception:
        logger.warning(
            "chat_context: falha ao limpar Redis tenant=%s",
            tenant_id,
            exc_info=True,
        )


def build_openai_messages(
    *,
    system_prompt: str,
    history: list[dict[str, str]],
    current_user_message: str,
) -> list[dict[str, Any]]:
    """Monta payload OpenAI: system + histórico + mensagem atual."""
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": system_prompt.strip()},
    ]
    for item in history:
        messages.append({"role": item["role"], "content": item["content"]})
    messages.append({"role": "user", "content": current_user_message.strip()})
    return messages

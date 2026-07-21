"""Estado temporário de digitação do cliente (cache, sem persistência)."""

from __future__ import annotations

from django.core.cache import cache

TYPING_TTL_SECONDS = 8


def typing_cache_key(tenant_id: int, session_id: int) -> str:
    return f"chat_typing:{int(tenant_id)}:{int(session_id)}"


def mark_typing(
    tenant_id: int,
    session_id: int,
    *,
    ttl: int = TYPING_TTL_SECONDS,
) -> None:
    cache.set(typing_cache_key(tenant_id, session_id), True, timeout=max(1, int(ttl)))


def clear_typing(tenant_id: int, session_id: int) -> None:
    cache.delete(typing_cache_key(tenant_id, session_id))


def is_client_typing(tenant_id: int, session_id: int) -> bool:
    return bool(cache.get(typing_cache_key(tenant_id, session_id)))

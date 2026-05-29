from __future__ import annotations

import logging
from typing import Any

from django.conf import settings

from apps.support.services.route_context import build_support_system_prompt

logger = logging.getLogger(__name__)


class SupportCopilotError(Exception):
    """Erro de configuração ou integração do copilot."""


class SupportCopilotServiceError(Exception):
    """Falha ao chamar a OpenAI."""


def _get_client():
    api_key = (settings.OPENAI_API_KEY or "").strip()
    if not api_key:
        raise SupportCopilotError("Serviço de IA não configurado.")
    from openai import OpenAI

    return OpenAI(api_key=api_key)


def _normalize_history(chat_history: list[dict[str, Any]] | None) -> list[dict[str, str]]:
    if not chat_history:
        return []
    max_items = getattr(settings, "SUPPORT_COPILOT_HISTORY_MAX", 20)
    normalized: list[dict[str, str]] = []
    for item in chat_history[-max_items:]:
        role = (item.get("role") or "").strip().lower()
        content = (item.get("content") or "").strip()
        if role not in ("user", "assistant") or not content:
            continue
        if len(content) > 2000:
            content = content[:2000]
        normalized.append({"role": role, "content": content})
    return normalized


def complete_support_chat(
    *,
    message: str,
    current_route: str,
    chat_history: list[dict[str, Any]] | None = None,
) -> str:
    user_text = (message or "").strip()
    if not user_text:
        raise SupportCopilotError("Mensagem vazia.")

    system = build_support_system_prompt(current_route)
    history = _normalize_history(chat_history)

    messages: list[dict[str, str]] = [{"role": "system", "content": system}]
    messages.extend(history)
    messages.append({"role": "user", "content": user_text})

    temperature = getattr(settings, "SUPPORT_COPILOT_TEMPERATURE", 0.3)
    max_tokens = getattr(settings, "SUPPORT_COPILOT_MAX_TOKENS", 500)

    try:
        client = _get_client()
        response = client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
    except SupportCopilotError:
        raise
    except Exception as exc:
        logger.warning("Support Copilot OpenAI error: %s", type(exc).__name__)
        raise SupportCopilotServiceError(
            "Não foi possível obter resposta do assistente. Tente novamente."
        ) from exc

    reply = (response.choices[0].message.content or "").strip()
    if not reply:
        raise SupportCopilotServiceError("Resposta vazia do assistente.")
    return reply

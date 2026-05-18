"""Histórico de mensagens por sessão (janela deslizante para OpenAI)."""

from __future__ import annotations

from django.conf import settings

from apps.residents.models import ChatMessage, ChatSession

DEFAULT_HISTORY_WINDOW = 6


def history_window_size() -> int:
    return int(getattr(settings, "OPENAI_HISTORY_WINDOW", DEFAULT_HISTORY_WINDOW))


def append_message(
    session: ChatSession,
    *,
    role: str,
    content: str,
) -> None:
    text = (content or "").strip()
    if not text:
        return
    ChatMessage.objects.create(
        session=session,
        role=role,
        content=text[:4000],
    )


def append_user_message(session: ChatSession, content: str) -> None:
    append_message(session, role=ChatMessage.Role.USER, content=content)


def append_assistant_message(session: ChatSession, content: str) -> None:
    append_message(session, role=ChatMessage.Role.ASSISTANT, content=content)


def get_sliding_history(session: ChatSession, *, limit: int | None = None) -> list[dict[str, str]]:
    """
    Retorna as últimas N mensagens (user/assistant) em ordem cronológica.
    Não inclui a mensagem system.
    """
    window = limit if limit is not None else history_window_size()
    rows = list(
        ChatMessage.objects.filter(session_id=session.pk)
        .order_by("-created_at")[:window],
    )
    rows.reverse()
    return [{"role": row.role, "content": row.content} for row in rows]

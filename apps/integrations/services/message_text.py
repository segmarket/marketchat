"""Extração de texto de mensagens do webhook Evolution GO."""

from __future__ import annotations

from typing import Any

_WRAPPER_KEYS = (
    "viewOnceMessage",
    "viewOnceMessageV2",
    "viewOnceMessageV2Extension",
    "ephemeralMessage",
    "documentWithCaptionMessage",
    "editedMessage",
)


def _ci_get(d: Any, *names: str) -> Any:
    if not isinstance(d, dict):
        return None
    for name in names:
        if name in d:
            return d[name]
    lowered = {k.lower(): k for k in d.keys() if isinstance(k, str)}
    for name in names:
        key = lowered.get(name.lower())
        if key is not None:
            return d[key]
    return None


def _unwrap_inner_message(message: dict[str, Any]) -> dict[str, Any]:
    cur = message
    for _ in range(8):
        next_inner = None
        for wrap_key in _WRAPPER_KEYS:
            wrapper = _ci_get(cur, wrap_key)
            if isinstance(wrapper, dict):
                inner = _ci_get(wrapper, "message", "Message")
                if isinstance(inner, dict) and inner:
                    next_inner = inner
                    break
        if next_inner is None:
            break
        cur = next_inner
    return cur


def extract_message_text(data: dict[str, Any]) -> str:
    """Extrai texto de conversation ou caption de mídia."""
    if not isinstance(data, dict):
        return ""

    message = _ci_get(data, "message", "Message")
    if not isinstance(message, dict):
        message = data

    inner = _unwrap_inner_message(message)

    conversation = _ci_get(inner, "conversation", "Conversation")
    if isinstance(conversation, str) and conversation.strip():
        return conversation.strip()

    for media_key in (
        "imageMessage",
        "ImageMessage",
        "videoMessage",
        "VideoMessage",
        "documentMessage",
        "DocumentMessage",
        "extendedTextMessage",
        "ExtendedTextMessage",
    ):
        media = _ci_get(inner, media_key)
        if isinstance(media, dict):
            caption = _ci_get(media, "caption", "Caption")
            if isinstance(caption, str) and caption.strip():
                return caption.strip()
            text = _ci_get(media, "text", "Text")
            if isinstance(text, str) and text.strip():
                return text.strip()

    return ""

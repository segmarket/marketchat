"""Detecção de tipos de mídia não suportados no webhook Evolution GO."""

from __future__ import annotations

from typing import Any

from apps.integrations.services.message_interactive import is_image_message
from apps.integrations.services.message_text import _ci_get, _unwrap_inner_message

UNSUPPORTED_MEDIA_KINDS = frozenset({"audio", "ptt", "video", "document"})

UNSUPPORTED_MEDIA_REPLY = (
    "Ops! 🙊 Ainda não consigo ouvir mensagens de áudio ou assistir vídeos.\n\n"
    "Por favor, digite em texto o que você precisa ou o nome do produto que está procurando!"
)

OUT_OF_CONTEXT_IMAGE_REPLY = (
    "Ops! 🙊 Ainda não consigo analisar imagens soltas por aqui "
    "(só uso fotos na hora de fechar o pagamento).\n\n"
    "Se você quer comprar algo, digite o nome do produto. "
    "Se está relatando algum problema no mercado, por favor, descreva o que aconteceu em texto!"
)

EMPTY_TEXT_FALLBACK_REPLY = "Não consegui entender, pode digitar novamente?"

_INNER_MESSAGE_KEYS = {
    "audio": ("audioMessage", "AudioMessage", "pttMessage", "PttMessage"),
    "video": ("videoMessage", "VideoMessage"),
    "document": ("documentMessage", "DocumentMessage"),
}

_MESSAGE_TYPE_ALIASES = {
    "audio": "audio",
    "audiomessage": "audio",
    "ptt": "ptt",
    "pttmessage": "ptt",
    "video": "video",
    "videomessage": "video",
    "document": "document",
    "documentmessage": "document",
}


def _normalize_message_type(raw: str) -> str | None:
    key = (raw or "").strip().lower().replace("_", "").replace("-", "")
    if not key:
        return None
    if key in _MESSAGE_TYPE_ALIASES:
        return _MESSAGE_TYPE_ALIASES[key]
    for prefix in ("audio", "ptt", "video", "document"):
        if key.startswith(prefix):
            return "ptt" if prefix == "ptt" or "ptt" in key else prefix
    return None


def _inner_message(data: dict[str, Any]) -> dict[str, Any]:
    message = _ci_get(data, "message", "Message")
    if not isinstance(message, dict):
        message = data
    return _unwrap_inner_message(message)


def _detect_ptt(inner: dict[str, Any]) -> bool:
    audio = _ci_get(inner, "audioMessage", "AudioMessage")
    if isinstance(audio, dict):
        ptt = _ci_get(audio, "ptt", "Ptt", "PTT")
        if ptt is True or str(ptt).lower() in ("true", "1"):
            return True
    return bool(_ci_get(inner, "pttMessage", "PttMessage"))


def detect_media_kind(data: dict[str, Any]) -> str | None:
    """Retorna audio | ptt | video | document. Imagem retorna None (fluxo AWAITING_PHOTO)."""
    if not isinstance(data, dict):
        return None

    if is_image_message(data):
        return None

    for field in ("messageType", "MessageType", "type", "Type"):
        declared = _ci_get(data, field)
        if isinstance(declared, str):
            normalized = _normalize_message_type(declared)
            if normalized in UNSUPPORTED_MEDIA_KINDS:
                return normalized

    info = _ci_get(data, "Info", "info")
    if isinstance(info, dict):
        for field in ("Type", "type", "MediaType", "mediaType"):
            declared = _ci_get(info, field)
            if isinstance(declared, str):
                normalized = _normalize_message_type(declared)
                if normalized in UNSUPPORTED_MEDIA_KINDS:
                    return normalized

    inner = _inner_message(data)

    if _detect_ptt(inner):
        return "ptt"

    for kind, keys in _INNER_MESSAGE_KEYS.items():
        if kind == "ptt":
            continue
        for key in keys:
            if _ci_get(inner, key):
                return kind
            if _ci_get(data, key):
                return kind

    return None


def event_is_unsupported_media(*, message_kind: str, raw_message: dict | None) -> bool:
    if message_kind in UNSUPPORTED_MEDIA_KINDS:
        return True
    if raw_message and isinstance(raw_message, dict):
        return detect_media_kind(raw_message) in UNSUPPORTED_MEDIA_KINDS
    return False

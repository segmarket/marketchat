"""Extração de respostas interativas e mídia do webhook Evolution GO."""

from __future__ import annotations

from typing import Any

from apps.integrations.services.message_text import _ci_get, _unwrap_inner_message


def _get_inner_message(data: dict[str, Any]) -> dict[str, Any]:
    message = _ci_get(data, "message", "Message")
    if not isinstance(message, dict):
        message = data
    return _unwrap_inner_message(message)


def extract_interactive_id(data: dict[str, Any]) -> str:
    """ID do botão ou linha de lista selecionada."""
    if not isinstance(data, dict):
        return ""
    inner = _get_inner_message(data)

    for key in (
        "buttonsResponseMessage",
        "ButtonsResponseMessage",
        "templateButtonReplyMessage",
        "TemplateButtonReplyMessage",
    ):
        block = _ci_get(inner, key)
        if isinstance(block, dict):
            selected = _ci_get(
                block,
                "selectedButtonId",
                "SelectedButtonId",
                "selectedId",
                "SelectedId",
            )
            if isinstance(selected, str) and selected.strip():
                return selected.strip()

    for key in ("listResponseMessage", "ListResponseMessage"):
        block = _ci_get(inner, key)
        if isinstance(block, dict):
            single = _ci_get(block, "singleSelectReply", "SingleSelectReply")
            if isinstance(single, dict):
                row_id = _ci_get(
                    single,
                    "selectedRowId",
                    "SelectedRowId",
                    "selectedId",
                    "SelectedId",
                )
                if isinstance(row_id, str) and row_id.strip():
                    return row_id.strip()
            row_id = _ci_get(block, "selectedRowId", "SelectedRowId")
            if isinstance(row_id, str) and row_id.strip():
                return row_id.strip()

    return ""


def is_image_message(data: dict[str, Any]) -> bool:
    if not isinstance(data, dict):
        return False
    inner = _get_inner_message(data)
    if _ci_get(inner, "imageMessage", "ImageMessage"):
        return True
    # Alguns payloads Evolution GO trazem a mídia no nível raiz de data.
    if _ci_get(data, "imageMessage", "ImageMessage"):
        return True
    return False


def event_has_image(
    *,
    message_kind: str,
    raw_message: dict[str, Any] | None,
) -> bool:
    """Detecta foto mesmo quando o parser classificou como text/unknown (ex.: legenda)."""
    if message_kind == "image":
        return True
    if not raw_message:
        return False
    return is_image_message({"message": raw_message}) or is_image_message(raw_message)


def extract_raw_message_dict(data: dict[str, Any]) -> dict[str, Any]:
    """Payload interno da mensagem para download de mídia."""
    if not isinstance(data, dict):
        return {}
    message = _ci_get(data, "message", "Message")
    if isinstance(message, dict):
        return message
    return data

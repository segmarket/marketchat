"""Parser de payloads do webhook Evolution GO."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from apps.integrations.services.message_interactive import (
    extract_interactive_id,
    extract_raw_message_dict,
    is_image_message,
)
from apps.integrations.services.message_media import detect_media_kind
from apps.integrations.services.message_text import extract_message_text


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


def _extract_message_meta(data: dict[str, Any]) -> tuple[str, str, bool]:
    info = _ci_get(data, "Info", "info")
    if isinstance(info, dict):
        remote = _ci_get(info, "Chat", "RemoteJid", "remoteJid") or ""
        msg_id = _ci_get(info, "ID", "Id", "id") or ""
        from_me = bool(_ci_get(info, "IsFromMe", "fromMe"))
        if remote and msg_id:
            return str(remote), str(msg_id), from_me

    key = _ci_get(data, "key") or {}
    if isinstance(key, dict):
        remote = _ci_get(key, "remoteJid", "RemoteJid") or ""
        msg_id = _ci_get(key, "id", "ID") or ""
        from_me = bool(_ci_get(key, "fromMe", "FromMe"))
        return str(remote), str(msg_id), from_me
    return "", "", False


@dataclass
class EvolutionWebhookEvent:
    event_type: str
    instance_key: str
    connection_state: str
    remote_jid: str
    message_id: str
    from_me: bool
    message_text: str = ""
    message_kind: str = "text"
    interactive_id: str = ""
    raw_message: dict | None = None
    presence: str = ""


def _extract_presence_status(data: dict[str, Any]) -> str:
    """Extrai status de presença (composing/typing/paused/…)."""
    for key in ("presence", "Presence", "presences", "status", "State", "state"):
        val = _ci_get(data, key)
        if isinstance(val, str) and val.strip():
            return val.strip().lower()
        if isinstance(val, dict):
            nested = _ci_get(val, "presence", "Presence", "status", "State", "state", "type")
            if isinstance(nested, str) and nested.strip():
                return nested.strip().lower()
    info = _ci_get(data, "Info", "info")
    if isinstance(info, dict):
        nested = _ci_get(info, "Presence", "presence", "Status", "status")
        if isinstance(nested, str) and nested.strip():
            return nested.strip().lower()
    return ""


def _extract_presence_jid(data: dict[str, Any]) -> str:
    """JID do contato em payloads de presença (nem sempre vêm em key/Info)."""
    remote, _, _ = _extract_message_meta(data)
    if remote:
        return remote
    for key in (
        "remoteJid",
        "RemoteJid",
        "chat",
        "Chat",
        "from",
        "From",
        "jid",
        "Jid",
        "participant",
        "Participant",
    ):
        val = _ci_get(data, key)
        if isinstance(val, str) and "@" in val:
            return val
        if isinstance(val, dict):
            nested = _ci_get(val, "remoteJid", "RemoteJid", "id", "Id")
            if isinstance(nested, str) and "@" in nested:
                return nested
    return ""


def parse_evolution_payload(body: dict[str, Any]) -> EvolutionWebhookEvent | None:
    if not body:
        return None

    event_type = str(
        _ci_get(body, "event", "Event", "type", "Type") or ""
    ).upper()
    data_root = body.get("data") if isinstance(body.get("data"), dict) else {}
    instance_key = str(
        _ci_get(body, "instance", "instanceName", "InstanceName", "instanceId", "name")
        or _ci_get(data_root, "instance", "instanceName", "InstanceName", "instanceId", "name")
        or ""
    )

    data = body.get("data")
    if not isinstance(data, dict):
        data = body

    connection_state = ""
    for key in ("state", "status", "connection", "connectionStatus"):
        val = _ci_get(data, key)
        if isinstance(val, str):
            raw_state = val.lower().strip()
            # Não confundir status de presença com estado de conexão.
            if raw_state in (
                "composing",
                "typing",
                "recording",
                "paused",
                "available",
                "unavailable",
                "online",
                "offline",
            ):
                break
            connection_state = raw_state
            break

    remote_jid, message_id, from_me = _extract_message_meta(data)
    presence = _extract_presence_status(data) if isinstance(data, dict) else ""
    if not remote_jid and isinstance(data, dict):
        remote_jid = _extract_presence_jid(data)

    message_text = extract_message_text(data) if isinstance(data, dict) else ""
    interactive_id = extract_interactive_id(data) if isinstance(data, dict) else ""
    raw_message = extract_raw_message_dict(data) if isinstance(data, dict) else {}

    message_kind = "text"
    if isinstance(data, dict):
        media_kind = detect_media_kind(data)
        if media_kind:
            message_kind = media_kind
        elif is_image_message(data):
            message_kind = "image"
        elif interactive_id:
            message_kind = "interactive"
        elif not message_text.strip():
            message_kind = "unknown"
    # Garante raw_message completo para download de mídia (Evolution GO).
    if isinstance(data, dict) and not raw_message:
        raw_message = data
    if "QRCODE" in event_type or event_type in ("QR", "QR_CODE", "QR_SUCCESS"):
        raw_message = data if isinstance(data, dict) else {"value": data}

    if not event_type and not instance_key:
        return None

    return EvolutionWebhookEvent(
        event_type=event_type,
        instance_key=instance_key,
        connection_state=connection_state,
        remote_jid=remote_jid,
        message_id=message_id,
        from_me=from_me,
        message_text=message_text,
        message_kind=message_kind,
        interactive_id=interactive_id,
        raw_message=raw_message or None,
        presence=presence,
    )


def map_connection_state(raw: str) -> str:
    v = (raw or "").strip().lower()
    if v in ("open", "connected"):
        return "open"
    if v in ("connecting", "pairing"):
        return "connecting"
    if v in ("close", "closed", "disconnected", "logout"):
        return "close"
    if v.startswith("401") or v.startswith("403"):
        return "close"
    if any(h in v for h in ("logged out", "disconnected", "logout", "forbidden")):
        return "close"
    return ""

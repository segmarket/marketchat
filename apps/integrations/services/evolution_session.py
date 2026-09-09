"""Gate de sessão Evolution: não pedir QR/connect após autenticação."""

from __future__ import annotations

import logging
import urllib.error
from dataclasses import dataclass
from typing import Any

from django.core.cache import cache

from apps.integrations.models import WhatsappInstance
from apps.integrations.services.evolution_client import EvolutionClient

logger = logging.getLogger(__name__)

QR_BLOCK_TTL_SECONDS = 120
OP_LOCK_TTL_SECONDS = 30
PAIRING_QR_TTL_SECONDS = 180

_LOGGED_IN_KEYS = ("loggedin", "logged_in", "isloggedin")
_CONNECTED_KEYS = ("connected", "isconnected")


def _qr_block_key(instance: WhatsappInstance) -> str:
    return f"evo_qr_block:{instance.pk}"


def _op_lock_key(instance: WhatsappInstance) -> str:
    return f"evo_op:{instance.pk}"


def _pairing_qr_key(instance: WhatsappInstance) -> str:
    return f"evo_pairing_qr:{instance.pk}"


@dataclass(frozen=True)
class RemoteSession:
    connected: bool
    logged_in: bool
    state: str

    @property
    def forbids_qr(self) -> bool:
        if self.logged_in:
            return True
        if self.state == WhatsappInstance.ConnectionStatus.OPEN:
            return True
        return bool(self.connected and self.state in ("", WhatsappInstance.ConnectionStatus.OPEN))

    @property
    def is_fully_connected(self) -> bool:
        if self.state == WhatsappInstance.ConnectionStatus.OPEN:
            return True
        return bool(self.logged_in and self.connected)


def _as_bool(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)) and value in (0, 1):
        return bool(value)
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in ("true", "1", "yes"):
            return True
        if lowered in ("false", "0", "no"):
            return False
    return None


def _find_bool(node: Any, names: tuple[str, ...], *, depth: int = 0) -> bool | None:
    if depth > 5 or not isinstance(node, dict):
        return None
    lowered = {str(k).lower(): v for k, v in node.items()}
    for name in names:
        if name in lowered:
            found = _as_bool(lowered[name])
            if found is not None:
                return found
    data = node.get("data")
    if isinstance(data, dict):
        nested = _find_bool(data, names, depth=depth + 1)
        if nested is not None:
            return nested
    return None


def parse_remote_session(payload: Any) -> RemoteSession:
    """Normaliza GET /instance/status (e payloads equivalentes) para flags de sessão."""
    if not isinstance(payload, dict):
        return RemoteSession(connected=False, logged_in=False, state="unknown")

    state = EvolutionClient.extract_connection_status(payload)
    logged_in = _find_bool(payload, _LOGGED_IN_KEYS)
    connected_flag = _find_bool(payload, _CONNECTED_KEYS)

    if state == WhatsappInstance.ConnectionStatus.OPEN and connected_flag is not False:
        if logged_in is None:
            logged_in = True
        if connected_flag is None:
            connected_flag = True

    logged_in = bool(logged_in)
    connected = bool(connected_flag) if connected_flag is not None else (
        state == WhatsappInstance.ConnectionStatus.OPEN
    )
    return RemoteSession(connected=connected, logged_in=logged_in, state=state or "unknown")


def is_qr_blocked(instance: WhatsappInstance) -> bool:
    return bool(cache.get(_qr_block_key(instance)))


def block_qr_after_connected(instance: WhatsappInstance, *, reason: str = "connected") -> None:
    cache.set(_qr_block_key(instance), "1", timeout=QR_BLOCK_TTL_SECONDS)
    clear_pairing_qr(instance)
    logger.info(
        "[Evolution] QR polling stopped instance=%s reason=%s",
        instance.instance_name,
        reason,
    )


def cache_pairing_qr(instance: WhatsappInstance, image: str) -> None:
    """Guarda o QR vindo do webhook/connect. Nunca dispara GET /instance/qr."""
    image = (image or "").strip()
    if not image:
        return
    if session_forbids_qr(instance):
        logger.info(
            "[Evolution] QR cache skipped instance=%s reason=already_logged_in",
            instance.instance_name,
        )
        return
    cache.set(_pairing_qr_key(instance), image, timeout=PAIRING_QR_TTL_SECONDS)
    logger.info(
        "[Evolution] QR cached from webhook instance=%s bytes=%s",
        instance.instance_name,
        len(image),
    )


def get_cached_pairing_qr(instance: WhatsappInstance) -> str:
    if session_forbids_qr(instance):
        return ""
    value = cache.get(_pairing_qr_key(instance)) or ""
    return value if isinstance(value, str) else ""


def clear_pairing_qr(instance: WhatsappInstance) -> None:
    cache.delete(_pairing_qr_key(instance))


def session_forbids_qr(
    instance: WhatsappInstance,
    remote: RemoteSession | None = None,
) -> bool:
    if instance.connection_status == WhatsappInstance.ConnectionStatus.OPEN:
        return True
    if is_qr_blocked(instance):
        return True
    if remote is not None:
        return remote.forbids_qr
    return False


def apply_authenticated_session(
    instance: WhatsappInstance,
    *,
    reason: str = "already_logged_in",
) -> None:
    """Marca a instância como OPEN e bloqueia QR subsequente."""
    update_fields = ["updated_at"]
    if instance.connection_status != WhatsappInstance.ConnectionStatus.OPEN:
        instance.connection_status = WhatsappInstance.ConnectionStatus.OPEN
        update_fields.append("connection_status")
    if instance.disconnect_reason:
        instance.disconnect_reason = ""
        update_fields.append("disconnect_reason")
    instance.save(update_fields=update_fields)
    block_qr_after_connected(instance, reason=reason)
    from apps.integrations.services.whatsapp_connection_alert import (
        on_whatsapp_connected,
    )

    on_whatsapp_connected(instance)


def inspect_remote_session(
    instance: WhatsappInstance,
    *,
    client: EvolutionClient | None = None,
) -> RemoteSession | None:
    """Consulta GET /instance/status. None = falha transitória (não libere QR às cegas)."""
    client = client or EvolutionClient()
    if not (instance.api_key or "").strip():
        return None
    try:
        payload = client.connection_state(instance_api_key=instance.api_key)
    except urllib.error.HTTPError as exc:
        if EvolutionClient._http_error_is_client_disconnected(exc):
            logger.info(
                "[Evolution] status instance=%s connected=false loggedIn=false "
                "(client disconnected)",
                instance.instance_name,
            )
            connecting = (
                instance.connection_status == WhatsappInstance.ConnectionStatus.CONNECTING
            )
            return RemoteSession(
                connected=False,
                logged_in=False,
                state=(
                    WhatsappInstance.ConnectionStatus.CONNECTING
                    if connecting
                    else WhatsappInstance.ConnectionStatus.CLOSE
                ),
            )
        logger.warning(
            "[Evolution] status instance=%s falhou: HTTP %s",
            instance.instance_name,
            exc.code,
        )
        return None
    except Exception as exc:
        logger.warning(
            "[Evolution] status instance=%s falhou: %s",
            instance.instance_name,
            type(exc).__name__,
        )
        return None

    session = parse_remote_session(payload)
    logger.info(
        "[Evolution] status instance=%s connected=%s loggedIn=%s",
        instance.instance_name,
        str(session.connected).lower(),
        str(session.logged_in).lower(),
    )
    return session


class EvolutionOpLock:
    """Lock Redis por instância (Gunicorn multi-worker). acquire() é idempotente."""

    def __init__(self, instance: WhatsappInstance, *, timeout: int = OP_LOCK_TTL_SECONDS):
        self.instance = instance
        self.timeout = timeout
        self._acquired = False

    def acquire(self) -> bool:
        if self._acquired:
            return True
        self._acquired = bool(
            cache.add(_op_lock_key(self.instance), "1", timeout=self.timeout)
        )
        return self._acquired

    def release(self) -> None:
        if not self._acquired:
            return
        cache.delete(_op_lock_key(self.instance))
        self._acquired = False

    def __enter__(self) -> bool:
        return self.acquire()

    def __exit__(self, *_exc: object) -> None:
        self.release()


def _connect_flight_key(instance_id: str) -> str:
    return f"evo_connect:{instance_id}"


def try_begin_connect_flight(instance_id: str) -> bool:
    """Single-flight de POST /instance/connect por instanceId."""
    key = (instance_id or "").strip()
    if not key:
        return True
    acquired = bool(cache.add(_connect_flight_key(key), "1", timeout=OP_LOCK_TTL_SECONDS))
    if not acquired:
        logger.info(
            "[Evolution] reconnect skipped instance=%s reason=operation_in_progress",
            key,
        )
    return acquired


def end_connect_flight(instance_id: str) -> None:
    key = (instance_id or "").strip()
    if key:
        cache.delete(_connect_flight_key(key))

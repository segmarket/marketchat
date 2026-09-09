"""Reconexão de sessão WhatsApp no Evolution GO (connect + QR, sem /instance/restart)."""

from __future__ import annotations

import logging

from django.conf import settings

from apps.integrations.models import WhatsappInstance
from apps.integrations.services.evolution_client import EvolutionClient
from apps.integrations.services.evolution_session import (
    EvolutionOpLock,
    end_connect_flight,
    get_cached_pairing_qr,
    inspect_remote_session,
    try_begin_connect_flight,
)
from apps.integrations.services.provisioning import (
    build_webhook_base_url,
    needs_hard_evolution_recreate,
    recreate_evolution_instance,
    sync_connection_status,
)

logger = logging.getLogger(__name__)


class EvolutionRestartError(Exception):
    pass


def _instance_webhook_url(instance: WhatsappInstance) -> str:
    raw = (instance.webhook_url or "").strip()
    if raw:
        # Repara URLs origin-only gravadas por engano (sem path do webhook).
        return EvolutionClient.build_webhook_url(raw, instance.webhook_secret)
    return EvolutionClient.build_webhook_url(
        build_webhook_base_url(),
        instance.webhook_secret,
    )


def _should_recreate_evolution_instance(instance: WhatsappInstance) -> bool:
    """
    Sessão não-open no Evolution quase sempre precisa de delete+create+connect.
    Só `connect`/`logout` em sessão invalidada pelo WhatsApp não gera QR
    (ver docs/production-whatsapp-evolution.md).
    """
    if needs_hard_evolution_recreate(instance):
        return True
    return instance.connection_status != WhatsappInstance.ConnectionStatus.OPEN


def _needs_session_reset(instance: WhatsappInstance) -> bool:
    """Sessão stale no Evolution exige logout/disconnect antes de novo connect."""
    reason = (instance.disconnect_reason or "").lower()
    if "qr code limit" in reason or "qrcode limit" in reason:
        return True
    if instance.connection_status == WhatsappInstance.ConnectionStatus.CLOSE:
        return True
    if "client disconnected" in reason or "desconectado" in reason:
        return True
    return False


def restart_whatsapp_instance(
    instance: WhatsappInstance,
    *,
    client: EvolutionClient | None = None,
) -> tuple[WhatsappInstance, str]:
    client = client or EvolutionClient()
    events = getattr(settings, "EVOLUTION_WEBHOOK_EVENTS", None) or list(
        EvolutionClient.DEFAULT_EVENTS
    )
    webhook_url = _instance_webhook_url(instance)
    if not webhook_url:
        raise EvolutionRestartError("URL do webhook não configurada para esta instância.")

    remote = inspect_remote_session(instance, client=client)
    if (
        instance.connection_status == WhatsappInstance.ConnectionStatus.OPEN
        or (remote is not None and remote.is_fully_connected)
    ):
        logger.info(
            "[Evolution] reconnect skipped instance=%s reason=already_logged_in",
            instance.instance_name,
        )
        try:
            sync_connection_status(instance, client=client)
        except Exception:
            logger.info(
                "[Evolution] status sync after skip reconnect instance=%s failed (ignored)",
                instance.instance_name,
            )
        instance.refresh_from_db()
        return instance, ""

    lock = EvolutionOpLock(instance)
    if not lock.acquire():
        logger.info(
            "[Evolution] reconnect skipped instance=%s reason=operation_in_progress",
            instance.instance_name,
        )
        instance.refresh_from_db()
        return instance, ""

    try:
        instance.refresh_from_db()
        if instance.connection_status == WhatsappInstance.ConnectionStatus.OPEN:
            return instance, ""
        if remote is not None and remote.logged_in and not remote.connected:
            logger.info(
                "[Evolution] reconnect without QR instance=%s reason=logged_in_disconnected",
                instance.instance_name,
            )
            if not try_begin_connect_flight(instance.instance_id):
                instance.refresh_from_db()
                return instance, ""
            try:
                client.reconnect_instance(
                    instance_api_key=instance.api_key,
                    webhook_url=webhook_url,
                    events=events,
                    reset_session=False,
                    wait_for_qr=False,
                )
            finally:
                end_connect_flight(instance.instance_id)
            instance.refresh_from_db()
            return instance, ""
        return _restart_pairing(
            instance,
            client=client,
            events=events,
            webhook_url=webhook_url,
        )
    except EvolutionRestartError:
        raise
    except Exception as exc:
        raise EvolutionRestartError(str(exc)) from exc
    finally:
        lock.release()


def _restart_pairing(
    instance: WhatsappInstance,
    *,
    client: EvolutionClient,
    events: list[str],
    webhook_url: str,
) -> tuple[WhatsappInstance, str]:
    reconnect_result: dict = {}
    recreated = False
    try:
        if _should_recreate_evolution_instance(instance):
            logger.info(
                "Restart %s: recriando instância no Evolution (sessão invalidada)",
                instance.instance_name,
            )
            instance = recreate_evolution_instance(instance, client=client)
            recreated = True
        else:
            if not try_begin_connect_flight(instance.instance_id):
                instance.refresh_from_db()
                return instance, get_cached_pairing_qr(instance)
            try:
                reconnect_result = client.reconnect_instance(
                    instance_api_key=instance.api_key,
                    webhook_url=webhook_url,
                    events=events,
                    reset_session=_needs_session_reset(instance),
                    wait_for_qr=False,
                )
            finally:
                end_connect_flight(instance.instance_id)
            instance.connection_status = WhatsappInstance.ConnectionStatus.CONNECTING
            instance.disconnect_reason = ""
            instance.save(
                update_fields=["connection_status", "disconnect_reason", "updated_at"]
            )
    except Exception as exc:
        raise EvolutionRestartError(str(exc)) from exc

    if recreated:
        logger.info(
            "Restart %s: instância recriada; QR via polling do painel",
            instance.instance_name,
        )
        return instance, ""

    qrcode_image = EvolutionClient.extract_qrcode_image(
        reconnect_result.get("qrcode") or reconnect_result.get("connect") or {}
    )
    if reconnect_result.get("qrcode", {}).get("connected"):
        instance.connection_status = WhatsappInstance.ConnectionStatus.OPEN
        instance.save(update_fields=["connection_status", "updated_at"])
        return instance, ""

    if qrcode_image:
        from apps.integrations.services.evolution_session import cache_pairing_qr

        cache_pairing_qr(instance, qrcode_image)
        return instance, qrcode_image

    logger.info(
        "Restart %s: connect OK, QR via webhook (GET /instance/qr skipped)",
        instance.instance_name,
    )
    return instance, ""

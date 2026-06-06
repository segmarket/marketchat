"""Reconexão de sessão WhatsApp no Evolution GO (connect + QR, sem /instance/restart)."""

from __future__ import annotations

import logging
import urllib.error

from django.conf import settings

from apps.integrations.models import WhatsappInstance
from apps.integrations.services.evolution_client import EvolutionClient
from apps.integrations.services.provisioning import (
    build_webhook_base_url,
    needs_hard_evolution_recreate,
    recreate_evolution_instance,
    refresh_qrcode,
)

logger = logging.getLogger(__name__)


class EvolutionRestartError(Exception):
    pass


def _instance_webhook_url(instance: WhatsappInstance) -> str:
    if (instance.webhook_url or "").strip():
        return instance.webhook_url.strip()
    return EvolutionClient.build_webhook_url(
        build_webhook_base_url(),
        instance.webhook_secret,
    )


def _should_recreate_evolution_instance(instance: WhatsappInstance) -> bool:
    """Sessão já conectada antes ou logout permanente exige novo token no Evolution."""
    if needs_hard_evolution_recreate(instance):
        return True
    if instance.connection_status != WhatsappInstance.ConnectionStatus.CLOSE:
        return False
    return bool(
        (instance.phone_number or "").strip()
        or (instance.profile_name or "").strip()
    )


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

    reconnect_result: dict = {}
    try:
        if _should_recreate_evolution_instance(instance):
            logger.info(
                "Restart %s: recriando instância no Evolution (sessão invalidada)",
                instance.instance_name,
            )
            instance = recreate_evolution_instance(instance, client=client)
        else:
            reconnect_result = client.reconnect_instance(
                instance_api_key=instance.api_key,
                webhook_url=webhook_url,
                events=events,
                reset_session=_needs_session_reset(instance),
                wait_for_qr=False,
            )
            instance.connection_status = WhatsappInstance.ConnectionStatus.CONNECTING
            instance.disconnect_reason = ""
            instance.save(
                update_fields=["connection_status", "disconnect_reason", "updated_at"]
            )
    except Exception as exc:
        raise EvolutionRestartError(str(exc)) from exc

    qrcode_image = EvolutionClient.extract_qrcode_image(
        reconnect_result.get("qrcode") or reconnect_result.get("connect") or {}
    )
    if reconnect_result.get("qrcode", {}).get("connected"):
        instance.connection_status = WhatsappInstance.ConnectionStatus.OPEN
        instance.save(update_fields=["connection_status", "updated_at"])
        return instance, ""

    if not qrcode_image:
        try:
            qr_result = refresh_qrcode(
                instance,
                client=client,
                skip_status_sync=True,
            )
            qrcode_image = qr_result.get("qrcode_image") or ""
            if qr_result.get("connected"):
                instance.connection_status = WhatsappInstance.ConnectionStatus.OPEN
                instance.save(update_fields=["connection_status", "updated_at"])
                return instance, ""
        except Exception as exc:
            if isinstance(exc, urllib.error.HTTPError):
                if EvolutionClient._http_error_is_qr_limit(exc):
                    raise EvolutionRestartError(
                        "Limite de QR Code atingido no Evolution. Desconecte e conecte "
                        "novamente para criar uma sessão limpa."
                    ) from exc
                if EvolutionClient._http_error_is_qr_not_ready(exc):
                    logger.info(
                        "Restart %s: connect OK, QR pendente (frontend fará polling)",
                        instance.instance_name,
                    )
                    return instance, ""
            if isinstance(exc, Exception) and "Limite de QR Code" in str(exc):
                raise EvolutionRestartError(str(exc)) from exc
            raise EvolutionRestartError(str(exc)) from exc

    return instance, qrcode_image

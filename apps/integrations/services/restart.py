"""Reconexão de sessão WhatsApp no Evolution GO (connect + QR, sem /instance/restart)."""

from __future__ import annotations

import urllib.error

from django.conf import settings

from apps.integrations.models import WhatsappInstance
from apps.integrations.services.evolution_client import EvolutionClient
from apps.integrations.services.instance_dashboard import sync_instance_from_evolution
from apps.integrations.services.provisioning import (
    build_webhook_base_url,
    refresh_qrcode,
)


class EvolutionRestartError(Exception):
    pass


def _instance_webhook_url(instance: WhatsappInstance) -> str:
    if (instance.webhook_url or "").strip():
        return instance.webhook_url.strip()
    return EvolutionClient.build_webhook_url(
        build_webhook_base_url(),
        instance.webhook_secret,
    )


def _needs_session_reset(instance: WhatsappInstance) -> bool:
    reason = (instance.disconnect_reason or "").lower()
    return "qr code limit" in reason or "qrcode limit" in reason


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

    try:
        client.reconnect_instance(
            instance_api_key=instance.api_key,
            webhook_url=webhook_url,
            events=events,
            phone=instance.pair_phone or "",
            reset_session=_needs_session_reset(instance),
        )
    except Exception as exc:
        raise EvolutionRestartError(str(exc)) from exc

    instance.connection_status = WhatsappInstance.ConnectionStatus.CONNECTING
    instance.disconnect_reason = ""
    instance.save(
        update_fields=["connection_status", "disconnect_reason", "updated_at"]
    )

    qrcode_image = ""
    try:
        qr_result = refresh_qrcode(instance, client=client)
        qrcode_image = qr_result.get("qrcode_image") or ""
        if qr_result.get("connected"):
            instance.connection_status = WhatsappInstance.ConnectionStatus.OPEN
            instance.save(update_fields=["connection_status", "updated_at"])
    except Exception as exc:
        if isinstance(exc, urllib.error.HTTPError) and EvolutionClient._http_error_is_qr_limit(
            exc
        ):
            raise EvolutionRestartError(
                "Limite de QR Code atingido no Evolution. Desconecte e conecte "
                "novamente para criar uma sessão limpa."
            ) from exc
        raise EvolutionRestartError(str(exc)) from exc

    instance = sync_instance_from_evolution(instance, client=client)
    return instance, qrcode_image

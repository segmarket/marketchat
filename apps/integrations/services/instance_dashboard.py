"""Payload enriquecido do painel WhatsApp para o front-end."""

from __future__ import annotations

from datetime import timedelta
from typing import Any

from django.utils import timezone

from apps.accounts.services.tenant_access import user_access_flags
from apps.integrations.models import WhatsappInstance
from apps.integrations.services.evolution_client import EvolutionClient
from apps.integrations.services.profile_sync import (
    apply_remote_row_to_instance,
    sync_profile_avatar_from_evolution,
)
from apps.integrations.services.provisioning import (
    reconcile_whatsapp_with_evolution,
    sync_connection_status,
)


WEBHOOK_OK_WINDOW = timedelta(minutes=10)
SESSION_EXPIRED_HINTS = (
    "expired",
    "qr code limit",
    "logout",
    "logged out",
    "another device",
    "401",
    "session",
)


def humanize_disconnect_reason(reason: str) -> str:
    """Traduz mensagens técnicas do Evolution para o painel."""
    text = (reason or "").strip()
    if not text:
        return ""
    lower = text.lower()
    if "qr code limit" in lower or "qrcode limit" in lower:
        return (
            "Limite de QR Code atingido (5 tentativas). Use Reconectar — se persistir, "
            "desconecte e conecte de novo para criar uma sessão limpa."
        )
    if "client disconnected" in lower:
        return "WhatsApp desconectado no celular. Gere um novo QR Code para reconectar."
    if "logged out" in lower and "another device" in lower:
        return (
            "WhatsApp desconectado em outro aparelho. Clique em Reconectar e escaneie "
            "um novo QR Code."
        )
    if lower.startswith("401") or "logged out" in lower:
        return (
            "Sessão encerrada no WhatsApp. Clique em Reconectar para gerar um novo QR Code."
        )
    return text


def _is_session_expired(instance: WhatsappInstance) -> bool:
    reason = (instance.disconnect_reason or "").lower()
    if any(hint in reason for hint in SESSION_EXPIRED_HINTS):
        return True
    if (
        instance.is_active
        and instance.connection_status == WhatsappInstance.ConnectionStatus.CLOSE
        and bool(instance.phone_number or instance.profile_name)
    ):
        return True
    return False


def _was_connected(instance: WhatsappInstance | None) -> bool:
    if not instance:
        return False
    return bool((instance.phone_number or "").strip() or (instance.profile_name or "").strip())


def _needs_reconnect(instance: WhatsappInstance | None) -> bool:
    if not instance:
        return False
    if instance.connection_status == WhatsappInstance.ConnectionStatus.OPEN:
        return False
    if not instance.is_active:
        return True
    return (
        _is_session_expired(instance)
        or instance.connection_status == WhatsappInstance.ConnectionStatus.CLOSE
    )


def _webhook_status(instance: WhatsappInstance | None) -> str:
    if not instance:
        return "unknown"
    if not instance.is_active:
        return "unknown"
    if not instance.last_webhook_at:
        return "error"
    if timezone.now() - instance.last_webhook_at <= WEBHOOK_OK_WINDOW:
        return "ok"
    return "error"


def sync_instance_from_evolution(
    instance: WhatsappInstance,
    *,
    client: EvolutionClient | None = None,
    refresh_avatar: bool = False,
) -> WhatsappInstance:
    client = client or EvolutionClient()
    if reconcile_whatsapp_with_evolution(instance, client=client) is None:
        return instance
    try:
        remote = client.fetch_remote_instance(instance_name=instance.instance_name)
        if remote:
            fields = apply_remote_row_to_instance(instance, remote)
            if fields:
                instance.save(update_fields=[*fields, "updated_at"])
    except Exception:
        pass
    if refresh_avatar:
        try:
            sync_profile_avatar_from_evolution(instance, client=client)
        except Exception:
            pass
    return instance


def build_dashboard_payload(
    instance: WhatsappInstance | None,
    *,
    request_user=None,
    qrcode_image: str = "",
    evolution_api_status: str | None = None,
    sync_evolution: bool = False,
    refresh_avatar: bool = False,
) -> dict[str, Any]:
    client = EvolutionClient()
    evo_status = evolution_api_status
    if evo_status is None:
        evo_status = client.check_evolution_health(timeout=3)

    if instance and instance.is_active and sync_evolution:
        sync_instance_from_evolution(
            instance,
            client=client,
            refresh_avatar=refresh_avatar,
        )
    elif (
        instance
        and instance.is_active
        and refresh_avatar
        and instance.connection_status == WhatsappInstance.ConnectionStatus.OPEN
    ):
        try:
            sync_profile_avatar_from_evolution(
                instance,
                client=client,
                try_both_previews=False,
            )
        except Exception:
            pass

    connected = bool(
        instance
        and instance.is_active
        and instance.connection_status == WhatsappInstance.ConnectionStatus.OPEN
    )

    data: dict[str, Any] = {
        "has_instance": bool(instance),
        "instance_name": instance.instance_name if instance else "",
        "connection_status": (
            instance.connection_status if instance else WhatsappInstance.ConnectionStatus.UNKNOWN
        ),
        "connected": connected,
        "is_active": bool(instance and instance.is_active),
        "was_connected": _was_connected(instance),
        "needs_reconnect": _needs_reconnect(instance),
        "pair_phone": instance.pair_phone if instance else "",
        "updated_at": instance.updated_at.isoformat() if instance else None,
        "profile_name": instance.profile_name if instance else "",
        "profile_picture_url": instance.profile_picture_url if instance else "",
        "phone_number": instance.phone_number if instance else "",
        "platform": instance.platform if instance else WhatsappInstance.Platform.UNKNOWN,
        "disconnect_reason": humanize_disconnect_reason(
            instance.disconnect_reason if instance else ""
        ),
        "session_expired": _is_session_expired(instance) if instance else False,
        "evolution_api_status": evo_status,
        "webhook_status": _webhook_status(instance),
        "qrcode_image": qrcode_image,
    }

    if request_user is not None and getattr(request_user, "is_authenticated", False):
        data.update(user_access_flags(request_user))

    return data

"""Provisionamento de instâncias WhatsApp no Evolution GO."""

from __future__ import annotations

import logging
import re
import secrets
import urllib.error
import uuid
from datetime import timedelta
from typing import Any

logger = logging.getLogger(__name__)

from django.conf import settings
from django.db import transaction

from apps.integrations.models import WhatsappInstance
from apps.integrations.services import evolution_client as evolution_client_module
from apps.integrations.services.evolution_client import EvolutionClient
from apps.tenants.models import Tenant


class WhatsappAlreadyProvisionedError(Exception):
    """Tenant já possui instância ativa."""


class EvolutionProvisionError(Exception):
    """Falha ao provisionar no Evolution GO."""

    def __init__(self, message: str, *, step: str = ""):
        super().__init__(message)
        self.step = step


STALE_EVOLUTION_REASON = (
    "A instância foi removida no Evolution. Clique em Conectar para vincular novamente."
)

SESSION_DISCONNECTED_REASON = (
    "WhatsApp desconectado no celular. Gere um novo QR Code para reconectar."
)

WEBHOOK_TRUST_WINDOW = timedelta(minutes=30)


def _evolution_http_error_is_stale(
    exc: urllib.error.HTTPError,
    *,
    client: EvolutionClient,
) -> bool:
    """Instância inexistente no Evolution (404). 401/403 são falha de credencial/rede."""
    del client
    return EvolutionClient._http_error_is_not_found(exc)


def _evolution_error_is_transient(
    exc: BaseException,
    *,
    client: EvolutionClient,
) -> bool:
    """Evolution fora do ar — não desativar instância local no painel."""
    del client
    if isinstance(exc, (urllib.error.URLError, OSError, TimeoutError)):
        return True
    if isinstance(exc, urllib.error.HTTPError):
        if EvolutionClient._http_error_is_not_found(exc):
            return False
        return exc.code in (401, 403, 408, 429, 500, 502, 503, 504) or exc.code >= 500
    return False


def remote_instance_exists(
    instance: WhatsappInstance,
    *,
    client: EvolutionClient | None = None,
) -> bool:
    client = client or EvolutionClient()
    name = (instance.instance_name or "").strip()
    if not name:
        return False
    try:
        return client.fetch_remote_instance(instance_name=name) is not None
    except urllib.error.HTTPError as exc:
        if EvolutionClient._http_error_is_not_found(exc):
            return False
        if _evolution_error_is_transient(exc, client=client):
            logger.warning(
                "Evolution indisponível ao verificar instância %s: HTTP %s",
                name,
                exc.code,
            )
            return True
        raise
    except (urllib.error.URLError, OSError, TimeoutError) as exc:
        logger.warning(
            "Evolution indisponível ao verificar instância %s: %s",
            name,
            exc,
        )
        return True


def _trust_local_open_connection(instance: WhatsappInstance) -> bool:
    """Webhook recente + status OPEN: não desativar se a listagem global do Evolution falhar."""
    if instance.connection_status != WhatsappInstance.ConnectionStatus.OPEN:
        return False
    if not instance.last_webhook_at:
        return False
    from django.utils import timezone

    return timezone.now() - instance.last_webhook_at <= WEBHOOK_TRUST_WINDOW


def mark_whatsapp_session_disconnected(
    instance: WhatsappInstance,
    *,
    reason: str = SESSION_DISCONNECTED_REASON,
) -> None:
    """Sessão WhatsApp caiu no Evolution; mantém registro ativo para reconexão no painel."""
    instance.is_active = True
    instance.connection_status = WhatsappInstance.ConnectionStatus.CLOSE
    instance.disconnect_reason = reason
    instance.save(
        update_fields=[
            "is_active",
            "connection_status",
            "disconnect_reason",
            "updated_at",
        ]
    )


def deactivate_stale_whatsapp_instance(
    instance: WhatsappInstance,
    *,
    reason: str = STALE_EVOLUTION_REASON,
) -> None:
    instance.is_active = False
    instance.connection_status = WhatsappInstance.ConnectionStatus.CLOSE
    instance.disconnect_reason = reason
    instance.save(
        update_fields=[
            "is_active",
            "connection_status",
            "disconnect_reason",
            "updated_at",
        ]
    )


def reconcile_whatsapp_with_evolution(
    instance: WhatsappInstance,
    *,
    client: EvolutionClient | None = None,
) -> WhatsappInstance | None:
    """
    Desativa registro local se a instância não existir mais no Evolution.
    Usa connection_state (apikey da instância) antes da listagem global — evita
    falso positivo quando /instance/all falha ou não lista o nome esperado.
    """
    if not instance.is_active:
        return instance
    client = client or EvolutionClient()
    try:
        status = sync_connection_status(instance, client=client)
        instance.refresh_from_db(fields=["connection_status", "is_active", "updated_at"])
        if status in (
            WhatsappInstance.ConnectionStatus.OPEN,
            WhatsappInstance.ConnectionStatus.CONNECTING,
        ):
            return instance
        if status == WhatsappInstance.ConnectionStatus.CLOSE:
            if remote_instance_exists(instance, client=client):
                return instance
            if instance.phone_number or instance.profile_name:
                return instance
    except EvolutionProvisionError:
        pass

    if remote_instance_exists(instance, client=client):
        return instance
    if _trust_local_open_connection(instance):
        return instance
    deactivate_stale_whatsapp_instance(instance)
    return None


def build_instance_name(tenant: Tenant) -> str:
    raw = f"mc-{tenant.slug}"[:200]
    safe = re.sub(r"[^a-zA-Z0-9_-]", "-", raw).strip("-").lower()
    return safe or f"mc-tenant-{tenant.pk}"


def build_webhook_base_url() -> str:
    base = (getattr(settings, "PUBLIC_WEBHOOK_BASE_URL", "") or "").rstrip("/")
    return f"{base}/api/integrations/webhooks/evolution/"


def _delete_remote_instance(
    client: EvolutionClient,
    *,
    instance_name: str = "",
    instance_id: str = "",
) -> None:
    try:
        client.delete_instance(instance_name=instance_name, instance_id=instance_id)
    except Exception:
        pass


@transaction.atomic
def provision_whatsapp_instance(
    tenant: Tenant,
    *,
    pair_phone: str = "",
    client: EvolutionClient | None = None,
) -> dict[str, Any]:
    client = client or EvolutionClient()
    existing = WhatsappInstance.all_objects.filter(tenant=tenant).first()
    if existing and existing.is_active:
        if (
            existing.connection_status == WhatsappInstance.ConnectionStatus.OPEN
            and remote_instance_exists(existing, client=client)
        ):
            raise WhatsappAlreadyProvisionedError("Este tenant já possui WhatsApp conectado.")
        if not remote_instance_exists(existing, client=client):
            deactivate_stale_whatsapp_instance(existing)

    instance_name = build_instance_name(tenant)
    instance_id = str(uuid.uuid4())
    token = secrets.token_urlsafe(32)
    webhook_secret = secrets.token_urlsafe(32)
    webhook_url = evolution_client_module.EvolutionClient.build_webhook_url(
        build_webhook_base_url(),
        webhook_secret,
    )
    events = getattr(settings, "EVOLUTION_WEBHOOK_EVENTS", None) or list(
        EvolutionClient.DEFAULT_EVENTS
    )

    if existing and not existing.is_active:
        _delete_remote_instance(
            client,
            instance_name=existing.instance_name or instance_name,
            instance_id=existing.instance_id,
        )
    else:
        _delete_remote_instance(client, instance_name=instance_name)

    try:
        create_payload = client.create_instance_safe(
            name=instance_name,
            instance_id=instance_id,
            token=token,
        )
    except Exception as exc:
        raise EvolutionProvisionError(str(exc), step="create") from exc

    try:
        connect_payload = client.connect_instance(
            instance_api_key=token,
            webhook_url=webhook_url,
            events=events,
            phone=pair_phone,
        )
    except Exception as exc:
        _delete_remote_instance(
            client, instance_name=instance_name, instance_id=instance_id
        )
        raise EvolutionProvisionError(str(exc), step="connect") from exc

    if existing:
        existing.instance_name = instance_name
        existing.instance_id = instance_id
        existing.api_key = token
        existing.webhook_url = webhook_url
        existing.webhook_secret = webhook_secret
        existing.pair_phone = pair_phone
        existing.connection_status = WhatsappInstance.ConnectionStatus.CONNECTING
        existing.disconnect_reason = ""
        existing.is_active = True
        existing.save(
            update_fields=[
                "instance_name",
                "instance_id",
                "api_key",
                "webhook_url",
                "webhook_secret",
                "pair_phone",
                "connection_status",
                "disconnect_reason",
                "is_active",
                "updated_at",
            ]
        )
        instance = existing
    else:
        instance = WhatsappInstance.objects.create(
            tenant=tenant,
            instance_name=instance_name,
            instance_id=instance_id,
            api_key=token,
            webhook_url=webhook_url,
            webhook_secret=webhook_secret,
            pair_phone=pair_phone,
            connection_status=WhatsappInstance.ConnectionStatus.CONNECTING,
            is_active=True,
        )

    qrcode_payload: dict[str, Any] = {}
    qrcode_image = ""
    try:
        qrcode_payload = client.fetch_qrcode(instance_api_key=token)
        if qrcode_payload.get("connected"):
            instance.connection_status = WhatsappInstance.ConnectionStatus.OPEN
            instance.save(update_fields=["connection_status", "updated_at"])
        else:
            qrcode_image = evolution_client_module.EvolutionClient.extract_qrcode_image(
                qrcode_payload
            )
    except Exception:
        pass

    return {
        "instance": instance,
        "create": create_payload,
        "connect": connect_payload,
        "qrcode": qrcode_payload,
        "qrcode_image": qrcode_image,
    }


def disconnect_whatsapp_instance(
    instance: WhatsappInstance,
    *,
    client: EvolutionClient | None = None,
) -> None:
    client = client or EvolutionClient()
    _delete_remote_instance(
        client,
        instance_name=instance.instance_name,
        instance_id=instance.instance_id,
    )
    instance.is_active = False
    instance.connection_status = WhatsappInstance.ConnectionStatus.CLOSE
    instance.disconnect_reason = ""
    instance.save(
        update_fields=[
            "is_active",
            "connection_status",
            "disconnect_reason",
            "updated_at",
        ]
    )


def refresh_qrcode(instance: WhatsappInstance, *, client: EvolutionClient | None = None) -> dict[str, Any]:
    client = client or EvolutionClient()
    if reconcile_whatsapp_with_evolution(instance, client=client) is None:
        raise EvolutionProvisionError(STALE_EVOLUTION_REASON, step="qrcode")
    payload = client.fetch_qrcode(instance_api_key=instance.api_key)
    if payload.get("connected"):
        instance.connection_status = WhatsappInstance.ConnectionStatus.OPEN
        instance.save(update_fields=["connection_status", "updated_at"])
        return {"connected": True, "qrcode_image": ""}
    image = evolution_client_module.EvolutionClient.extract_qrcode_image(payload)
    if instance.connection_status != WhatsappInstance.ConnectionStatus.OPEN:
        instance.connection_status = WhatsappInstance.ConnectionStatus.CONNECTING
        instance.save(update_fields=["connection_status", "updated_at"])
    return {"connected": False, "qrcode_image": image, "raw": payload}


def sync_connection_status(
    instance: WhatsappInstance,
    *,
    client: EvolutionClient | None = None,
) -> str:
    client = client or EvolutionClient()
    try:
        payload = client.connection_state(instance_api_key=instance.api_key)
    except urllib.error.HTTPError as exc:
        if evolution_client_module.EvolutionClient._http_error_is_client_disconnected(exc):
            mark_whatsapp_session_disconnected(instance)
            logger.info(
                "WhatsApp sessão desconectada no Evolution: %s",
                instance.instance_name,
            )
            return WhatsappInstance.ConnectionStatus.CLOSE
        if _evolution_http_error_is_stale(exc, client=client):
            deactivate_stale_whatsapp_instance(instance)
            return WhatsappInstance.ConnectionStatus.CLOSE
        if _evolution_error_is_transient(exc, client=client):
            logger.warning(
                "Evolution indisponível ao sincronizar status de %s: HTTP %s",
                instance.instance_name,
                exc.code,
            )
            return instance.connection_status
        raise EvolutionProvisionError(str(exc), step="connection_state") from exc
    except (urllib.error.URLError, OSError, TimeoutError) as exc:
        logger.warning(
            "Evolution inacessível ao sincronizar status de %s: %s",
            instance.instance_name,
            exc,
        )
        return instance.connection_status
    status = evolution_client_module.EvolutionClient.extract_connection_status(payload)
    if status in WhatsappInstance.ConnectionStatus.values:
        instance.connection_status = status
        update_fields = ["connection_status", "updated_at"]
        if status == WhatsappInstance.ConnectionStatus.OPEN:
            instance.disconnect_reason = ""
            update_fields.append("disconnect_reason")
        instance.save(update_fields=update_fields)
    return instance.connection_status

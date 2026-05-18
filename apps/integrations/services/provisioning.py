"""Provisionamento de instâncias WhatsApp no Evolution GO."""

from __future__ import annotations

import re
import secrets
import uuid
from typing import Any

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
    existing = WhatsappInstance.all_objects.filter(tenant=tenant).first()
    if existing and existing.is_active:
        raise WhatsappAlreadyProvisionedError("Este tenant já possui WhatsApp conectado.")

    client = client or EvolutionClient()
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
    instance.save(update_fields=["is_active", "connection_status", "updated_at"])


def refresh_qrcode(instance: WhatsappInstance, *, client: EvolutionClient | None = None) -> dict[str, Any]:
    client = client or EvolutionClient()
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
    payload = client.connection_state(instance_api_key=instance.api_key)
    status = evolution_client_module.EvolutionClient.extract_connection_status(payload)
    if status in WhatsappInstance.ConnectionStatus.values:
        instance.connection_status = status
        instance.save(update_fields=["connection_status", "updated_at"])
    return instance.connection_status

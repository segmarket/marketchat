"""Alerta de desconexão WhatsApp: espelho no Tenant + e-mail com debounce."""

from __future__ import annotations

import logging
import threading
import uuid

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache

from apps.core.emails import send_whatsapp_disconnected_email_safe
from apps.integrations.models import WhatsappInstance
from apps.tenants.models import Tenant

logger = logging.getLogger(__name__)
User = get_user_model()

DISCONNECT_EMAIL_DELAY_SECONDS = int(
    getattr(settings, "WHATSAPP_DISCONNECT_EMAIL_DELAY_SECONDS", 120)
)
_PENDING_CACHE_TTL = max(DISCONNECT_EMAIL_DELAY_SECONDS + 60, 180)
_SENT_CACHE_TTL = 3600


def _pending_cache_key(tenant_id: int) -> str:
    return f"wa_disconnect_email:{tenant_id}"


def _sent_cache_key(tenant_id: int) -> str:
    return f"wa_disconnect_email_sent:{tenant_id}"


def set_whatsapp_connected(tenant_id: int, *, connected: bool) -> bool:
    """Atualiza Tenant.is_whatsapp_connected. Retorna True se o valor mudou."""
    updated = (
        Tenant.objects.filter(pk=tenant_id)
        .exclude(is_whatsapp_connected=connected)
        .update(is_whatsapp_connected=connected)
    )
    return updated > 0


def cancel_pending_disconnect_email(tenant_id: int) -> None:
    cache.delete(_pending_cache_key(tenant_id))


def on_whatsapp_connected(instance: WhatsappInstance) -> None:
    set_whatsapp_connected(instance.tenant_id, connected=True)
    cancel_pending_disconnect_email(instance.tenant_id)


def on_whatsapp_disconnected(
    instance: WhatsappInstance,
    *,
    schedule_email: bool = True,
) -> None:
    set_whatsapp_connected(instance.tenant_id, connected=False)
    if not schedule_email:
        return

    token = str(uuid.uuid4())
    cache.set(_pending_cache_key(instance.tenant_id), token, timeout=_PENDING_CACHE_TTL)
    timer = threading.Timer(
        DISCONNECT_EMAIL_DELAY_SECONDS,
        send_disconnect_email_if_still_down,
        args=(instance.tenant_id, instance.pk, token),
    )
    timer.daemon = True
    timer.start()
    logger.info(
        "WhatsApp disconnect email agendado em %ss: tenant=%s token=%s",
        DISCONNECT_EMAIL_DELAY_SECONDS,
        instance.tenant_id,
        token[:8],
    )


def send_disconnect_email_if_still_down(
    tenant_id: int,
    instance_id: int,
    token: str,
) -> None:
    """Callback do Timer: envia e-mail só se ainda desconectado e token válido."""
    pending = cache.get(_pending_cache_key(tenant_id))
    if pending != token:
        logger.info(
            "WhatsApp disconnect email cancelado (token inválido): tenant=%s",
            tenant_id,
        )
        return

    try:
        instance = WhatsappInstance.all_objects.get(pk=instance_id)
    except WhatsappInstance.DoesNotExist:
        cache.delete(_pending_cache_key(tenant_id))
        return

    if instance.connection_status == WhatsappInstance.ConnectionStatus.OPEN:
        cancel_pending_disconnect_email(tenant_id)
        set_whatsapp_connected(tenant_id, connected=True)
        return

    if cache.get(_sent_cache_key(tenant_id)):
        cancel_pending_disconnect_email(tenant_id)
        logger.info(
            "WhatsApp disconnect email já enviado recentemente: tenant=%s",
            tenant_id,
        )
        return

    tenant = Tenant.objects.filter(pk=tenant_id).first()
    if tenant is None:
        cancel_pending_disconnect_email(tenant_id)
        return

    admins = list(
        User.objects.filter(tenant_id=tenant_id, is_tenant_admin=True)
        .exclude(email="")
        .order_by("pk")
    )
    if not admins:
        logger.warning(
            "WhatsApp desconectado sem admin para e-mail: tenant=%s",
            tenant_id,
        )
        cancel_pending_disconnect_email(tenant_id)
        return

    for admin in admins:
        send_whatsapp_disconnected_email_safe(admin, tenant)

    cache.set(_sent_cache_key(tenant_id), "1", timeout=_SENT_CACHE_TTL)
    cancel_pending_disconnect_email(tenant_id)
    logger.info(
        "WhatsApp disconnect email enviado: tenant=%s recipients=%s",
        tenant_id,
        len(admins),
    )

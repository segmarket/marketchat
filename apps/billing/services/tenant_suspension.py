from __future__ import annotations

import logging
import threading

from django.db import transaction

from apps.integrations.models import WhatsappInstance
from apps.integrations.services.provisioning import disconnect_whatsapp_instance
from apps.tenants.models import Tenant

logger = logging.getLogger(__name__)


def _disconnect_whatsapp_for_tenant(tenant_id: int) -> None:
    instances = WhatsappInstance.all_objects.filter(
        tenant_id=tenant_id,
        is_active=True,
    )
    for instance in instances:
        try:
            disconnect_whatsapp_instance(instance)
            logger.info(
                "WhatsApp desconectado por suspensão: tenant=%s instance=%s",
                tenant_id,
                instance.instance_name,
            )
        except Exception:
            logger.exception(
                "Falha ao desconectar WhatsApp tenant=%s instance=%s",
                tenant_id,
                instance.instance_name,
            )


def suspend_tenant_for_overdue(tenant: Tenant) -> None:
    """Suspende tenant inadimplente (após carência) e desativa WhatsApp."""
    if tenant.subscription_status == Tenant.SubscriptionStatus.SUSPENDED:
        return

    tenant.subscription_status = Tenant.SubscriptionStatus.SUSPENDED
    tenant.block_billing_access()
    tenant.save(
        update_fields=["subscription_status", "billing_blocked_at", "updated_at"],
    )

    tenant_id = tenant.pk
    transaction.on_commit(
        lambda: threading.Thread(
            target=_disconnect_whatsapp_for_tenant,
            args=(tenant_id,),
            daemon=True,
        ).start(),
    )


def tenant_has_messaging_access(tenant_id: int) -> bool:
    """Bloqueia processamento de mensagens WhatsApp para tenant suspenso."""
    tenant = Tenant.objects.filter(pk=tenant_id).only(
        "subscription_status",
        "overdue_since",
        "billing_blocked_at",
    ).first()
    if tenant is None:
        return False
    if tenant.subscription_status == Tenant.SubscriptionStatus.SUSPENDED:
        return False
    if tenant.billing_blocked_at is not None:
        return False
    if tenant.subscription_status == Tenant.SubscriptionStatus.OVERDUE:
        return tenant.is_in_grace_period()
    return True

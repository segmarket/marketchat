from __future__ import annotations

from apps.integrations.models import WhatsappInstance


def get_tenant_whatsapp_instance(tenant_id: int) -> WhatsappInstance | None:
    """Último registro WhatsApp do tenant (ativo ou inativo) para exibição no painel."""
    return (
        WhatsappInstance.all_objects.filter(tenant_id=tenant_id)
        .order_by("-id")
        .first()
    )


def get_active_whatsapp_instance(tenant_id: int) -> WhatsappInstance | None:
    return (
        WhatsappInstance.objects.filter(tenant_id=tenant_id, is_active=True)
        .order_by("-id")
        .first()
    )

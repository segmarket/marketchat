"""Alerta ao dono do mercado via WhatsApp."""

from __future__ import annotations

import logging
import re

from django.contrib.auth import get_user_model

from apps.integrations.models import WhatsappInstance
from apps.residents.models import Resident
from apps.residents.services.whatsapp_reply import send_whatsapp_reply
from apps.tenants.models import Tenant

logger = logging.getLogger(__name__)

User = get_user_model()

SUPPORT_RESIDENT_MESSAGE = (
    "Lamentamos o transtorno! Já registrei o seu chamado de suporte e o responsável "
    "pelo mercado do condomínio foi avisado para resolver o problema o quanto antes."
)


def resolve_tenant_owner_phone(tenant_id: int) -> str:
    try:
        tenant = Tenant.objects.get(pk=tenant_id)
        phone = re.sub(r"\D", "", tenant.phone or "")
        if phone:
            return phone
    except Tenant.DoesNotExist:
        pass

    admin = (
        User.objects.filter(tenant_id=tenant_id, is_tenant_admin=True)
        .exclude(phone="")
        .order_by("id")
        .first()
    )
    if admin:
        return re.sub(r"\D", "", admin.phone or "")

    any_user = User.objects.filter(tenant_id=tenant_id).exclude(phone="").order_by("id").first()
    if any_user:
        return re.sub(r"\D", "", any_user.phone or "")
    return ""


def build_owner_alert_body(
    *,
    resident: Resident,
    original_message: str,
    issue_label: str,
) -> str:
    market_name = resident.market.name if resident.market_id else "Mercado não informado"
    return (
        f"Alerta de suporte ({issue_label})\n"
        f"Morador: {resident.name or 'Sem nome'}\n"
        f"Telefone: {resident.phone_number}\n"
        f"Condomínio: {market_name}\n"
        f"Mensagem: {original_message.strip()}"
    )


def build_owner_restock_body(
    *,
    resident: Resident,
    product_label: str,
) -> str:
    market_name = resident.market.name if resident.market_id else "Condomínio"
    resident_name = resident.name or resident.phone_number
    product = product_label.strip() or "produto não identificado"
    return (
        f"📦 ALERTA DE REPOSIÇÃO - {market_name}\n\n"
        f"O morador {resident_name} relatou que o produto {product} está em falta na gôndola."
    )


def notify_owner_restock_issue(
    *,
    instance: WhatsappInstance,
    resident: Resident,
    product_label: str,
    original_message: str,
) -> None:
    owner_phone = resolve_tenant_owner_phone(resident.tenant_id)
    body = build_owner_restock_body(resident=resident, product_label=product_label)
    if not owner_phone:
        logger.warning(
            "Alerta de reposição ignorado: sem telefone do tenant=%s",
            resident.tenant_id,
        )
        return
    send_whatsapp_reply(instance, owner_phone, body)
    logger.info(
        "Alerta reposição enviado: tenant=%s produto=%r msg=%r",
        resident.tenant_id,
        product_label,
        original_message[:80],
    )


def notify_owner_support_issue(
    *,
    instance: WhatsappInstance,
    tenant_id: int,
    resident: Resident,
    original_message: str,
    issue_label: str,
) -> None:
    owner_phone = resolve_tenant_owner_phone(tenant_id)
    body = build_owner_alert_body(
        resident=resident,
        original_message=original_message,
        issue_label=issue_label,
    )
    if not owner_phone:
        logger.warning(
            "Alerta ao dono ignorado: sem telefone do tenant=%s",
            tenant_id,
        )
        return
    send_whatsapp_reply(instance, owner_phone, body)

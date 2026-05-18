"""Handlers de eventos do webhook Evolution GO."""

from __future__ import annotations

import logging

from apps.integrations.models import WhatsappInstance
from apps.integrations.services.profile_sync import sync_profile_avatar_from_evolution
from apps.integrations.services.webhook_parser import EvolutionWebhookEvent, map_connection_state
from apps.chatbot.services.flow_engine import run_chatbot_flow
from apps.residents.services.onboarding_flow import (
    process_inbound_message,
    resident_has_completed_onboarding,
)
from apps.residents.models import Resident
from apps.sales.services.cart_escape import handle_global_escape
from apps.sales.services.cart_flow import process_cart_flow
from apps.residents.services.phone import jid_to_phone
from apps.tenants.context import tenant_scope

logger = logging.getLogger(__name__)


def handle_evolution_webhook(event: EvolutionWebhookEvent, instance: WhatsappInstance) -> None:
    with tenant_scope(instance.tenant_id):
        event_name = event.event_type
        if "CONNECTION" in event_name:
            _handle_connection(event, instance)
        elif "QRCODE" in event_name or "QR" in event_name:
            _handle_qrcode(instance)
        elif "MESSAGE" in event_name:
            _handle_message(event, instance)
        else:
            logger.info(
                "Webhook Evolution ignorado: event=%s instance=%s",
                event_name,
                instance.instance_name,
            )


def _handle_connection(event: EvolutionWebhookEvent, instance: WhatsappInstance) -> None:
    status = map_connection_state(event.connection_state)
    if not status:
        return
    if instance.connection_status != status:
        instance.connection_status = status
        instance.save(update_fields=["connection_status", "updated_at"])
    if status == WhatsappInstance.ConnectionStatus.OPEN:
        sync_profile_avatar_from_evolution(instance)
    logger.info(
        "WhatsApp connection: tenant=%s instance=%s status=%s",
        instance.tenant_id,
        instance.instance_name,
        status,
    )


def _handle_qrcode(instance: WhatsappInstance) -> None:
    if instance.connection_status != WhatsappInstance.ConnectionStatus.OPEN:
        instance.connection_status = WhatsappInstance.ConnectionStatus.CONNECTING
        instance.save(update_fields=["connection_status", "updated_at"])
    logger.info("WhatsApp QR update: instance=%s", instance.instance_name)


def _handle_message(event: EvolutionWebhookEvent, instance: WhatsappInstance) -> None:
    if event.from_me or (event.remote_jid and event.remote_jid.endswith("@g.us")):
        return

    phone = jid_to_phone(event.remote_jid)
    if not phone:
        return

    text = (event.message_text or "").strip()

    if not resident_has_completed_onboarding(instance.tenant_id, phone):
        if not text:
            logger.info(
                "WhatsApp MESSAGE sem texto (onboarding): tenant=%s jid=%s",
                instance.tenant_id,
                event.remote_jid,
            )
            return
        process_inbound_message(instance.tenant_id, instance, phone, text)
        return

    if text:
        resident = (
            Resident.objects.filter(
                tenant_id=instance.tenant_id,
                phone_number=phone,
                market__isnull=False,
            )
            .first()
        )
        if resident and handle_global_escape(
            instance=instance,
            phone=phone,
            resident=resident,
            text=text,
        ):
            return

    if process_cart_flow(instance.tenant_id, instance, phone, event):
        return

    if not text:
        logger.info(
            "WhatsApp MESSAGE sem texto (mídia/ignorada): tenant=%s jid=%s kind=%s",
            instance.tenant_id,
            event.remote_jid,
            event.message_kind,
        )
        return

    if run_chatbot_flow(instance.tenant_id, instance, phone, text):
        return

    logger.info(
        "WhatsApp MESSAGE (sem fluxo ativo): tenant=%s instance=%s phone=%s msg_id=%s text=%r",
        instance.tenant_id,
        instance.instance_name,
        phone,
        event.message_id,
        text[:80],
    )

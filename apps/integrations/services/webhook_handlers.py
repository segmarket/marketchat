"""Handlers de eventos do webhook Evolution GO."""

from __future__ import annotations

import logging

from apps.chatbot.models import ChatMessageLog
from apps.chatbot.services.chat_logging import get_or_create_chat_session, log_inbound
from apps.residents.services.session_activity import touch_chat_session_activity
from apps.residents.services.session_lazy_expiration import maybe_reset_stale_chat_session
from apps.integrations.models import WhatsappInstance
from apps.integrations.services.message_interactive import event_has_image
from apps.integrations.services.message_media import (
    EMPTY_TEXT_FALLBACK_REPLY,
    OUT_OF_CONTEXT_IMAGE_REPLY,
    UNSUPPORTED_MEDIA_REPLY,
    event_is_unsupported_media,
)
from apps.residents.services.whatsapp_reply import send_whatsapp_reply
from apps.integrations.services.profile_sync import sync_profile_avatar_from_evolution
from apps.integrations.services.provisioning import (
    SESSION_DISCONNECTED_REASON,
    mark_whatsapp_session_disconnected,
)
from apps.integrations.services.webhook_parser import EvolutionWebhookEvent, map_connection_state
from apps.chatbot.services.flow_engine import run_chatbot_flow
from apps.residents.services.onboarding_flow import (
    process_inbound_message,
    resident_has_completed_onboarding,
)
from apps.residents.models import ChatSession, Resident
from apps.sales.services.cart_escape import handle_global_escape
from apps.sales.services.cart_flow import process_cart_flow
from apps.sales.services.intent_gatekeeper import GENERAL, classify_user_intent
from apps.residents.services.phone import jid_to_phone
from apps.tenants.context import tenant_scope

logger = logging.getLogger(__name__)


def handle_evolution_webhook(event: EvolutionWebhookEvent, instance: WhatsappInstance) -> None:
    with tenant_scope(instance.tenant_id):
        event_name = event.event_type
        # CONNECTED ≠ substring de CONNECTION — tratar eventos explícitos do Evolution GO.
        if event_name in ("CONNECTED", "PAIRSUCCESS"):
            _handle_connected(event, instance)
        elif event_name in ("DISCONNECTED", "LOGOUT"):
            _handle_disconnected(instance)
        elif "CONNECTION" in event_name or event.connection_state:
            _handle_connection(event, instance)
        elif "QRCODE" in event_name or "QR" in event_name:
            _handle_qrcode(instance)
        elif "MESSAGE" in event_name or event_name.startswith("MESSAGES"):
            _handle_message(event, instance)
        else:
            logger.info(
                "Webhook Evolution ignorado: event=%s instance=%s",
                event_name,
                instance.instance_name,
            )


def _handle_connected(event: EvolutionWebhookEvent, instance: WhatsappInstance) -> None:
    """CONNECTED / PAIRSUCCESS: sessão ativa no Evolution GO."""
    status = map_connection_state(event.connection_state) or WhatsappInstance.ConnectionStatus.OPEN
    if instance.connection_status != status:
        instance.connection_status = status
        instance.save(update_fields=["connection_status", "updated_at"])
    if status == WhatsappInstance.ConnectionStatus.OPEN:
        sync_profile_avatar_from_evolution(instance)
    logger.info(
        "WhatsApp connected: tenant=%s instance=%s event=%s status=%s",
        instance.tenant_id,
        instance.instance_name,
        event.event_type,
        status,
    )


def _handle_disconnected(instance: WhatsappInstance) -> None:
    mark_whatsapp_session_disconnected(
        instance,
        reason="WhatsApp desconectado no aparelho.",
    )
    logger.info(
        "WhatsApp disconnected: tenant=%s instance=%s",
        instance.tenant_id,
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
    from apps.billing.services.tenant_suspension import tenant_has_messaging_access

    logger.info(
        "WhatsApp MESSAGE recebido: tenant=%s instance=%s jid=%s text_len=%s",
        instance.tenant_id,
        instance.instance_name,
        event.remote_jid,
        len((event.message_text or "").strip()),
    )

    if not tenant_has_messaging_access(instance.tenant_id):
        logger.info(
            "WhatsApp MESSAGE ignorado (tenant sem acesso): tenant=%s",
            instance.tenant_id,
        )
        return

    if event.from_me or (event.remote_jid and event.remote_jid.endswith("@g.us")):
        return

    phone = jid_to_phone(event.remote_jid)
    if not phone:
        return

    if event_is_unsupported_media(
        message_kind=event.message_kind,
        raw_message=event.raw_message,
    ):
        send_whatsapp_reply(
            instance, phone, UNSUPPORTED_MEDIA_REPLY, record_context=False,
        )
        logger.info(
            "WhatsApp MESSAGE mídia não suportada: tenant=%s phone=%s kind=%s",
            instance.tenant_id,
            phone,
            event.message_kind,
        )
        return

    text = (event.message_text or "").strip()
    has_image = event_has_image(
        message_kind=event.message_kind,
        raw_message=event.raw_message,
    )
    session = get_or_create_chat_session(instance.tenant_id, phone)

    resident_for_lazy = (
        Resident.objects.filter(
            tenant_id=instance.tenant_id,
            phone_number=phone,
        )
        .select_related("market")
        .first()
    )
    if maybe_reset_stale_chat_session(session, resident=resident_for_lazy):
        session.refresh_from_db()

    touch_chat_session_activity(session)
    onboarded = resident_has_completed_onboarding(instance.tenant_id, phone)

    if (
        onboarded
        and has_image
        and session.state != ChatSession.State.AWAITING_PHOTO
    ):
        send_whatsapp_reply(
            instance, phone, OUT_OF_CONTEXT_IMAGE_REPLY, record_context=False,
        )
        logger.info(
            "WhatsApp MESSAGE imagem fora de AWAITING_PHOTO: tenant=%s state=%s",
            instance.tenant_id,
            session.state,
        )
        return

    if onboarded and text:
        from apps.chatbot.services.chat_context_cache import append_message

        append_message(
            instance.tenant_id,
            phone,
            role="user",
            content=text,
        )

    intent_type = ""
    if onboarded and text and session.state == ChatSession.State.IDLE:
        intent_type = classify_user_intent(
            text,
            tenant_id=instance.tenant_id,
            phone=phone,
        )
    elif not onboarded:
        intent_type = GENERAL

    message_kind = ChatMessageLog.MessageKind.TEXT
    if event.message_kind == "interactive":
        message_kind = ChatMessageLog.MessageKind.INTERACTIVE
    elif has_image:
        message_kind = ChatMessageLog.MessageKind.IMAGE

    # Fotos de carrinho são registradas em evolution_media com attachment.
    if message_kind != ChatMessageLog.MessageKind.IMAGE:
        log_inbound(
            tenant_id=instance.tenant_id,
            phone=phone,
            message_text=text,
            intent_type=intent_type,
            session=session,
            message_kind=message_kind,
            evolution_message_id=event.message_id or "",
        )

    if not onboarded:
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
            resident_for_lazy
            if resident_for_lazy and resident_for_lazy.market_id
            else None
        )
        if resident is None:
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

    session.refresh_from_db(fields=["state"])
    if session.state != ChatSession.State.IDLE:
        if not text and not (
            has_image and session.state == ChatSession.State.AWAITING_PHOTO
        ):
            logger.info(
                "WhatsApp MESSAGE ignorada fora de IDLE: tenant=%s state=%s kind=%s",
                instance.tenant_id,
                session.state,
                event.message_kind,
            )
        return

    if not text:
        logger.info(
            "WhatsApp MESSAGE sem texto (fallback): tenant=%s jid=%s kind=%s",
            instance.tenant_id,
            event.remote_jid,
            event.message_kind,
        )
        send_whatsapp_reply(
            instance, phone, EMPTY_TEXT_FALLBACK_REPLY, record_context=False,
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

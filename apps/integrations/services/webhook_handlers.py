"""Handlers de eventos do webhook Evolution GO."""

from __future__ import annotations

import logging

from django.core.cache import cache

from apps.chatbot.models import ChatMessageLog
from apps.chatbot.services.chat_logging import (
    get_or_create_chat_session,
    log_inbound,
    log_inbound_image,
)
from apps.chatbot.services.typing_presence import clear_typing, mark_typing
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
from apps.core.pii import mask_jid
from apps.residents.services.phone import jid_to_phone
from apps.tenants.context import tenant_scope

logger = logging.getLogger(__name__)

_TYPING_ACTIVE = frozenset({"composing", "typing", "recording"})
_TYPING_CLEAR = frozenset({"paused", "available", "unavailable", "online", "offline"})


def handle_evolution_webhook(event: EvolutionWebhookEvent, instance: WhatsappInstance) -> None:
    with tenant_scope(instance.tenant_id):
        event_name = event.event_type
        # CONNECTED ≠ substring de CONNECTION — tratar eventos explícitos do Evolution GO.
        if event_name in ("CONNECTED", "PAIRSUCCESS"):
            _handle_connected(event, instance)
        elif event_name in ("DISCONNECTED", "LOGOUT"):
            _handle_disconnected(instance)
        elif (
            "PRESENCE" in event_name
            or event_name in ("COMPOSING", "TYPING", "RECORDING", "PAUSED")
            or event.presence in _TYPING_ACTIVE | _TYPING_CLEAR
        ):
            # Antes de CONNECTION: payloads de presença usam status/state e não devem
            # ser interpretados como mudança de conexão WhatsApp.
            _handle_presence(event, instance)
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


def _handle_presence(event: EvolutionWebhookEvent, instance: WhatsappInstance) -> None:
    if event.from_me or (event.remote_jid and event.remote_jid.endswith("@g.us")):
        return

    phone = jid_to_phone(event.remote_jid)
    if not phone:
        return

    presence = (event.presence or "").strip().lower()
    if not presence:
        # Alguns payloads usam o próprio event_type como status.
        presence = event.event_type.strip().lower()
        if presence.startswith("presence"):
            presence = ""

    if not presence:
        return

    session = get_or_create_chat_session(instance.tenant_id, phone)
    if presence in _TYPING_ACTIVE:
        mark_typing(instance.tenant_id, session.id)
        logger.debug(
            "Presence typing: tenant=%s session=%s presence=%s",
            instance.tenant_id,
            session.id,
            presence,
        )
    elif presence in _TYPING_CLEAR:
        clear_typing(instance.tenant_id, session.id)


def _handle_connected(event: EvolutionWebhookEvent, instance: WhatsappInstance) -> None:
    """CONNECTED / PAIRSUCCESS: sessão ativa no Evolution GO."""
    status = map_connection_state(event.connection_state) or WhatsappInstance.ConnectionStatus.OPEN
    if instance.connection_status != status:
        instance.connection_status = status
        instance.save(update_fields=["connection_status", "updated_at"])
    if status == WhatsappInstance.ConnectionStatus.OPEN:
        from apps.integrations.services.whatsapp_connection_alert import (
            on_whatsapp_connected,
        )

        on_whatsapp_connected(instance)
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
    update_fields = ["connection_status", "updated_at"]
    if status == WhatsappInstance.ConnectionStatus.CLOSE:
        reason = (event.connection_state or "").strip()
        if reason and reason != instance.disconnect_reason:
            instance.disconnect_reason = reason
            update_fields.append("disconnect_reason")
    elif status == WhatsappInstance.ConnectionStatus.OPEN:
        if instance.disconnect_reason:
            instance.disconnect_reason = ""
            update_fields.append("disconnect_reason")
    if instance.connection_status != status:
        instance.connection_status = status
        instance.save(update_fields=update_fields)
    elif len(update_fields) > 2:
        instance.save(update_fields=update_fields)

    from apps.integrations.services.whatsapp_connection_alert import (
        on_whatsapp_connected,
        on_whatsapp_disconnected,
    )

    if status == WhatsappInstance.ConnectionStatus.OPEN:
        on_whatsapp_connected(instance)
        sync_profile_avatar_from_evolution(instance)
    elif status == WhatsappInstance.ConnectionStatus.CLOSE:
        on_whatsapp_disconnected(instance)
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
        mask_jid(event.remote_jid),
        len((event.message_text or "").strip()),
    )

    message_id = (event.message_id or "").strip()
    if message_id:
        dedup_key = f"evo_webhook_msg:{instance.tenant_id}:{message_id}"
        try:
            if not cache.add(dedup_key, "1", timeout=120):
                logger.info(
                    "WhatsApp MESSAGE duplicado ignorado: tenant=%s msg_id=%s",
                    instance.tenant_id,
                    message_id,
                )
                return
        except Exception:
            logger.warning(
                "Falha no dedup de MESSAGE (seguindo): tenant=%s msg_id=%s",
                instance.tenant_id,
                message_id,
                exc_info=True,
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

    clear_typing(instance.tenant_id, session.id)

    resident_for_lazy = (
        Resident.objects.filter(
            tenant_id=instance.tenant_id,
            phone_number=phone,
            is_anonymized=False,
            is_active=True,
        )
        .select_related("market")
        .first()
    )
    if maybe_reset_stale_chat_session(session, resident=resident_for_lazy):
        session.refresh_from_db()

    touch_chat_session_activity(session)
    onboarded = resident_has_completed_onboarding(instance.tenant_id, phone)

    from apps.chatbot.services.human_handover import ensure_bot_active_or_timeout
    from apps.chatbot.services.bot_schedule import should_bot_auto_reply
    from apps.tenants.models import Tenant

    tenant = (
        Tenant.objects.filter(pk=instance.tenant_id)
        .only("is_bot_active_global")
        .first()
    )
    bot_should_reply = bool(tenant and tenant.is_bot_active_global)
    if not bot_should_reply:
        logger.info(
            "Bot desligado pela chave geral: tenant=%s phone=%s",
            instance.tenant_id,
            phone,
        )
    else:
        bot_should_reply = ensure_bot_active_or_timeout(session)
        if bot_should_reply and not should_bot_auto_reply(instance.tenant_id):
            bot_should_reply = False
            logger.info(
                "Bot pausado no horário comercial: tenant=%s phone=%s",
                instance.tenant_id,
                phone,
            )

    message_kind = ChatMessageLog.MessageKind.TEXT
    if event.message_kind == "interactive":
        message_kind = ChatMessageLog.MessageKind.INTERACTIVE
    elif has_image:
        message_kind = ChatMessageLog.MessageKind.IMAGE

    # Sempre registra no histórico — imagens com attachment para o inbox.
    if message_kind == ChatMessageLog.MessageKind.IMAGE:
        image_bytes = None
        if event.raw_message:
            from apps.sales.services.evolution_media import download_security_photo_bytes

            image_bytes = download_security_photo_bytes(
                instance=instance,
                raw_message=event.raw_message,
            )
        log_inbound_image(
            tenant_id=instance.tenant_id,
            phone=phone,
            session=session,
            evolution_message_id=event.message_id or "",
            resident=resident_for_lazy,
            caption=text,
            attachment_name=f"inbound_{event.message_id or session.id}.jpg",
            attachment_bytes=image_bytes,
        )
        if not image_bytes:
            logger.warning(
                "Imagem inbound sem bytes (log sem attachment): tenant=%s msg=%s",
                instance.tenant_id,
                event.message_id,
            )

    if (
        bot_should_reply
        and onboarded
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

    if onboarded and text and bot_should_reply:
        from apps.chatbot.services.chat_context_cache import append_message

        append_message(
            instance.tenant_id,
            phone,
            role="user",
            content=text,
        )

    intent_type = ""
    if bot_should_reply and onboarded and text and session.state == ChatSession.State.IDLE:
        intent_type = classify_user_intent(
            text,
            tenant_id=instance.tenant_id,
            phone=phone,
        )
    elif not onboarded:
        intent_type = GENERAL

    if message_kind != ChatMessageLog.MessageKind.IMAGE:
        log_inbound(
            tenant_id=instance.tenant_id,
            phone=phone,
            message_text=text,
            intent_type=intent_type,
            session=session,
            message_kind=message_kind,
            evolution_message_id=event.message_id or "",
            resident=resident_for_lazy,
        )

    if not bot_should_reply:
        from apps.sales.services.handlers.payment import (
            try_escape_human_queue_for_purchase,
        )

        if text and try_escape_human_queue_for_purchase(
            instance=instance,
            phone=phone,
            text=text,
            session=session,
            resident=resident_for_lazy,
        ):
            return
        logger.info(
            "WhatsApp MESSAGE em atendimento humano (bot pausado): tenant=%s phone=%s",
            instance.tenant_id,
            phone,
        )
        return

    if not onboarded:
        if not text:
            logger.info(
                "WhatsApp MESSAGE sem texto (onboarding): tenant=%s jid=%s",
                instance.tenant_id,
                mask_jid(event.remote_jid),
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
                    is_anonymized=False,
                    is_active=True,
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
            mask_jid(event.remote_jid),
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

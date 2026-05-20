"""Persistência de mensagens WhatsApp para central de atendimento."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from django.core.files.base import ContentFile

from apps.chatbot.models import ChatMessageLog
from apps.residents.models import ChatSession, Resident

if TYPE_CHECKING:
    from apps.integrations.models import WhatsappInstance
    from apps.sales.models import Cart

logger = logging.getLogger(__name__)

INTENT_PRIORITY: tuple[str, ...] = (
    ChatMessageLog.IntentType.MAINTENANCE_ISSUE,
    ChatMessageLog.IntentType.COMPLAINT,
    ChatMessageLog.IntentType.PAYMENT_ERROR,
    ChatMessageLog.IntentType.STOCK_ISSUE,
    ChatMessageLog.IntentType.PURCHASE,
    ChatMessageLog.IntentType.GENERAL,
)


def normalize_intent(intent_type: str | None) -> str:
    value = (intent_type or "").strip().upper()
    if value in ChatMessageLog.IntentType.values:
        return value
    return ""


def pick_dominant_intent(intents: list[str]) -> str:
    normalized = {normalize_intent(i) for i in intents if normalize_intent(i)}
    for candidate in INTENT_PRIORITY:
        if candidate in normalized:
            return candidate
    return ChatMessageLog.IntentType.GENERAL


def resolve_resident_for_phone(tenant_id: int, phone: str) -> Resident | None:
    return (
        Resident.objects.filter(
            tenant_id=tenant_id,
            phone_number=phone,
            market__isnull=False,
        )
        .select_related("market")
        .first()
    )


def get_or_create_chat_session(tenant_id: int, phone: str) -> ChatSession:
    session, _ = ChatSession.objects.get_or_create(
        tenant_id=tenant_id,
        phone_number=phone,
        defaults={"state": ChatSession.State.IDLE},
    )
    return session


def _create_log(
    *,
    tenant_id: int,
    session: ChatSession,
    direction: str,
    message_text: str,
    intent_type: str = "",
    message_kind: str = ChatMessageLog.MessageKind.TEXT,
    resident: Resident | None = None,
    cart: Cart | None = None,
    evolution_message_id: str = "",
    attachment_name: str = "",
    attachment_bytes: bytes | None = None,
) -> ChatMessageLog | None:
    if resident is None:
        resident = resolve_resident_for_phone(tenant_id, session.phone_number)

    market_id = resident.market_id if resident and resident.market_id else None

    log = ChatMessageLog(
        tenant_id=tenant_id,
        session=session,
        resident=resident,
        market_id=market_id,
        cart=cart,
        message_text=(message_text or "")[:8000],
        direction=direction,
        intent_type=normalize_intent(intent_type),
        message_kind=message_kind or ChatMessageLog.MessageKind.TEXT,
        evolution_message_id=(evolution_message_id or "")[:128],
    )
    log.save()

    if attachment_bytes and attachment_name:
        log.attachment.save(attachment_name, ContentFile(attachment_bytes), save=True)

    return log


def log_inbound(
    *,
    tenant_id: int,
    phone: str,
    message_text: str,
    intent_type: str = "",
    session: ChatSession | None = None,
    message_kind: str = ChatMessageLog.MessageKind.TEXT,
    evolution_message_id: str = "",
    resident: Resident | None = None,
) -> ChatMessageLog | None:
    if not phone:
        return None
    session = session or get_or_create_chat_session(tenant_id, phone)
    from apps.residents.services.session_activity import touch_chat_session_activity

    touch_chat_session_activity(session)
    return _create_log(
        tenant_id=tenant_id,
        session=session,
        direction=ChatMessageLog.Direction.INBOUND,
        message_text=message_text,
        intent_type=intent_type,
        message_kind=message_kind,
        evolution_message_id=evolution_message_id,
        resident=resident,
    )


def log_outbound(
    *,
    instance: WhatsappInstance,
    phone: str,
    message_text: str,
    intent_type: str = "",
    session: ChatSession | None = None,
    cart: Cart | None = None,
) -> ChatMessageLog | None:
    if not phone or not (message_text or "").strip():
        return None
    tenant_id = instance.tenant_id
    session = session or get_or_create_chat_session(tenant_id, phone)
    from apps.residents.services.session_activity import touch_chat_session_activity

    touch_chat_session_activity(session)
    return _create_log(
        tenant_id=tenant_id,
        session=session,
        direction=ChatMessageLog.Direction.OUTBOUND,
        message_text=message_text,
        intent_type=intent_type,
        cart=cart,
    )


def log_inbound_image_from_cart(
    *,
    tenant_id: int,
    session: ChatSession,
    cart: Cart,
    resident: Resident | None = None,
    evolution_message_id: str = "",
) -> ChatMessageLog | None:
    """Registra foto de segurança enviada pelo morador (cópia do arquivo do carrinho)."""
    if not cart.product_photo:
        return None
    try:
        cart.product_photo.open("rb")
        data = cart.product_photo.read()
        cart.product_photo.close()
    except Exception:
        logger.exception("Falha ao ler product_photo para log cart=%s", cart.id)
        return None

    name = cart.product_photo.name.split("/")[-1] or f"cart-{cart.id}.jpg"
    return _create_log(
        tenant_id=tenant_id,
        session=session,
        direction=ChatMessageLog.Direction.INBOUND,
        message_text="[Foto dos produtos]",
        intent_type=ChatMessageLog.IntentType.PURCHASE,
        message_kind=ChatMessageLog.MessageKind.IMAGE,
        evolution_message_id=evolution_message_id,
        resident=resident,
        cart=cart,
        attachment_name=name,
        attachment_bytes=data,
    )

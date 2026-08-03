"""Orquestra um turno do chatbot demo (sem Evolution)."""

from __future__ import annotations

import hashlib
import logging
import uuid
from typing import Any

from apps.chatbot.services.human_handover import resume_bot, should_mute_for_human
from apps.demo.services.portal import ensure_demo_portal
from apps.integrations.services.message_media import OUT_OF_CONTEXT_IMAGE_REPLY
from apps.integrations.services.webhook_parser import EvolutionWebhookEvent
from apps.residents.models import ChatSession, Resident
from apps.residents.services.onboarding_flow import (
    process_inbound_message,
    resident_has_completed_onboarding,
)
from apps.residents.services.whatsapp_reply import (
    capture_demo_replies,
    send_whatsapp_reply,
)
from apps.sales.models import Cart
from apps.sales.services.cart_flow import process_cart_flow
from apps.sales.services.maquininha_backup import try_escape_human_queue_for_purchase
from apps.tenants.context import tenant_scope

logger = logging.getLogger(__name__)

DEMO_MEDIA_MARKER = "[MEDIA:IMAGE]"

DEMO_BLOCKING_RESET_MESSAGE = (
    "💡 [Simulação]: No mundo real, nossa equipe humana estaria conversando "
    "com você agora! Como este é um ambiente de testes, acabei de reiniciar "
    "nosso chat. Pode testar outro cenário!"
)

DEMO_EMPTY_REPLY_FALLBACK = (
    "Poxa, parece que minha conexão falhou por um instante. "
    "Você pode repetir, por favor?"
)


def normalize_session_id(raw: str | None) -> str:
    text = (raw or "").strip()
    if not text:
        return str(uuid.uuid4())
    try:
        return str(uuid.UUID(text))
    except ValueError:
        # Aceita ids opacos: deriva UUID estável
        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
        return str(uuid.UUID(digest[:32]))


def session_id_to_demo_phone(session_id: str) -> str:
    """Telefone sintético só com dígitos (Evolution/send filtram isdigit)."""
    digest = hashlib.sha256(session_id.encode("utf-8")).hexdigest()
    num = int(digest[:13], 16) % (10**11)
    return f"55{num:011d}"


def _is_media_turn(*, message: str, is_media: bool) -> bool:
    if is_media:
        return True
    return (message or "").strip() == DEMO_MEDIA_MARKER


def _demo_payment_waiting(session: ChatSession | None) -> bool:
    if session is None or not session.active_cart_id:
        return False
    cart = session.active_cart
    return bool(cart and cart.status == Cart.Status.AWAITING_PAYMENT)


def _reset_demo_session(session: ChatSession) -> None:
    """Limpa FSM/contexto da sessão demo para o visitante continuar testando."""
    session.state = ChatSession.State.IDLE
    session.pending_intent = ""
    session.temporary_name = ""
    session.pending_product = None
    session.last_discussed_product = None
    session.active_cart = None
    session.save(
        update_fields=[
            "state",
            "pending_intent",
            "temporary_name",
            "pending_product",
            "last_discussed_product",
            "active_cart",
            "updated_at",
        ],
    )
    if not session.is_bot_active:
        resume_bot(session)


def process_demo_chat_turn(
    *,
    message: str,
    session_id: str | None,
    is_media: bool = False,
) -> dict[str, Any]:
    sid = normalize_session_id(session_id)
    phone = session_id_to_demo_phone(sid)
    text = (message or "").strip()
    media = _is_media_turn(message=text, is_media=is_media)

    if not media and not text:
        return {"reply": "", "session_id": sid}

    bundle = ensure_demo_portal()
    tenant = bundle.tenant
    instance = bundle.instance

    with tenant_scope(tenant.id), capture_demo_replies() as replies:
        try:
            session = ChatSession.objects.filter(
                tenant_id=tenant.id,
                phone_number=phone,
            ).first()

            # Demo: escape de compra quebra mute; senão estados bloqueantes resetam.
            if session is not None and (
                should_mute_for_human(session) or _demo_payment_waiting(session)
            ):
                from apps.sales.services.maquininha_backup import (
                    try_escape_human_queue_for_purchase,
                )

                escaped = False
                if (
                    not media
                    and text
                    and session.state == ChatSession.State.WAITING_FOR_HUMAN
                ):
                    resident = Resident.objects.filter(
                        tenant_id=tenant.id,
                        phone_number=phone,
                        market__isnull=False,
                        is_anonymized=False,
                        is_active=True,
                    ).first()
                    escaped = try_escape_human_queue_for_purchase(
                        instance=instance,
                        phone=phone,
                        text=text,
                        session=session,
                        resident=resident,
                    )
                if not escaped:
                    logger.info(
                        "demo_chat auto-reset bloqueio session=%s phone=%s state=%s bot_active=%s",
                        sid,
                        phone,
                        session.state,
                        session.is_bot_active,
                    )
                    _reset_demo_session(session)
                    send_whatsapp_reply(
                        instance,
                        phone,
                        DEMO_BLOCKING_RESET_MESSAGE,
                        record_context=False,
                    )
            elif media:
                onboarded = resident_has_completed_onboarding(tenant.id, phone)
                awaiting_photo = bool(
                    onboarded
                    and session
                    and session.state == ChatSession.State.AWAITING_PHOTO
                )
                if not awaiting_photo:
                    send_whatsapp_reply(
                        instance,
                        phone,
                        OUT_OF_CONTEXT_IMAGE_REPLY,
                        record_context=False,
                    )
                else:
                    event = EvolutionWebhookEvent(
                        event_type="MESSAGE",
                        instance_key=instance.instance_name or "demo",
                        connection_state="",
                        remote_jid=f"{phone}@s.whatsapp.net",
                        message_id=f"demo-{uuid.uuid4().hex[:16]}",
                        from_me=False,
                        message_text="",
                        message_kind="image",
                        raw_message={"imageMessage": {"demoSimulated": True}},
                    )
                    process_cart_flow(tenant.id, instance, phone, event)
            elif not resident_has_completed_onboarding(tenant.id, phone):
                process_inbound_message(tenant.id, instance, phone, text)
            else:
                event = EvolutionWebhookEvent(
                    event_type="MESSAGE",
                    instance_key=instance.instance_name or "demo",
                    connection_state="",
                    remote_jid=f"{phone}@s.whatsapp.net",
                    message_id=f"demo-{uuid.uuid4().hex[:16]}",
                    from_me=False,
                    message_text=text,
                    message_kind="text",
                )
                process_cart_flow(tenant.id, instance, phone, event)
        except Exception:
            logger.exception(
                "demo_chat falha no turno session=%s phone=%s media=%s",
                sid,
                phone,
                media,
            )
            if not any(r.strip() for r in replies):
                send_whatsapp_reply(
                    instance,
                    phone,
                    DEMO_EMPTY_REPLY_FALLBACK,
                    record_context=False,
                )

    reply = "\n\n".join(r for r in replies if r.strip())
    if not reply:
        reply = DEMO_EMPTY_REPLY_FALLBACK
    logger.info(
        "demo_chat turn session=%s phone=%s media=%s replies=%s",
        sid,
        phone,
        media,
        len(replies),
    )
    return {"reply": reply, "session_id": sid}

"""Venda backup (Pix) quando a maquininha física falha + fuga do mute humano."""

from __future__ import annotations

import logging

from apps.chatbot.services.chat_history import append_assistant_message
from apps.chatbot.services.human_handover import resume_bot
from apps.integrations.models import WhatsappInstance
from apps.notifications.services import create_critical_panel_notification
from apps.residents.models import ChatSession, Resident
from apps.residents.services.whatsapp_reply import send_whatsapp_reply
from apps.sales.services.cart_repository import get_or_create_open_cart
from apps.sales.services.intent_gatekeeper import PAYMENT_ERROR
from apps.sales.services.owner_alert import notify_owner_support_issue

logger = logging.getLogger(__name__)

MACHINE_BACKUP_SALE_MESSAGE = (
    "Vi que a maquininha está fora. Já notifiquei o suporte, mas você não precisa "
    "deixar suas compras! Você pode pagar os produtos por aqui mesmo via Pix. "
    "O que você deseja levar?"
)

SUPPORT_PAYMENT_BACKUP_SALE_MESSAGE = (
    "Sua notificação foi registrada para a equipe técnica resolver a máquina física. 🛠️ "
    "Mas não se preocupe, você não precisa deixar seus produtos! Podemos finalizar a "
    "sua venda por aqui mesmo via Pix. Me diga, qual produto você deseja levar?"
)

HUMAN_QUEUE_PURCHASE_ESCAPE_MESSAGE = (
    "Como vi que você quer levar produtos, vou te ajudar com o pagamento por aqui "
    "enquanto o atendente não chega! Me diga, o que você quer comprar?"
)

PURCHASE_ESCAPE_KEYWORDS = ("comprar", "levar", "pagar", "pix", "produto")


def text_has_purchase_escape_intent(text: str) -> bool:
    lowered = (text or "").lower()
    return any(word in lowered for word in PURCHASE_ESCAPE_KEYWORDS)


def start_maquininha_backup_sale(
    *,
    instance: WhatsappInstance,
    tenant_id: int,
    phone: str,
    resident: Resident,
    session: ChatSession,
    message: str = "",
    notify: bool = True,
    issue_label: str = "Pagamento",
    reply_text: str | None = None,
) -> None:
    """Notifica suporte (opcional) e abre PRODUCT_SEARCH como PDV Pix alternativo."""
    body = (reply_text or MACHINE_BACKUP_SALE_MESSAGE).strip()
    if notify:
        notify_owner_support_issue(
            instance=instance,
            tenant_id=tenant_id,
            resident=resident,
            original_message=message or "Problema na maquininha física",
            issue_label=issue_label,
        )
        create_critical_panel_notification(
            tenant_id=tenant_id,
            resident=resident,
            intent_type=PAYMENT_ERROR,
            original_message=message or "Problema na maquininha física",
        )

    if not session.is_bot_active:
        resume_bot(session)

    cart = get_or_create_open_cart(resident)
    session.active_cart = cart
    session.temporary_name = ""
    session.pending_product = None
    session.pending_intent = ""
    session.state = ChatSession.State.PRODUCT_SEARCH
    session.save(
        update_fields=[
            "active_cart",
            "temporary_name",
            "pending_product",
            "pending_intent",
            "state",
            "updated_at",
        ],
    )
    send_whatsapp_reply(
        instance,
        phone,
        body,
        session=session,
    )
    append_assistant_message(session, body)
    logger.info(
        "maquininha backup sale tenant=%s phone=%s session=%s",
        tenant_id,
        phone,
        session.pk,
    )


def try_escape_human_queue_for_purchase(
    *,
    instance: WhatsappInstance,
    phone: str,
    text: str,
    session: ChatSession | None,
    resident: Resident | None = None,
) -> bool:
    """
    Quebra WAITING_FOR_HUMAN quando o morador sinaliza intenção de compra.
    Retorna True se tratou (mute não deve engolir a mensagem).
    """
    if session is None or session.state != ChatSession.State.WAITING_FOR_HUMAN:
        return False
    if not text_has_purchase_escape_intent(text):
        return False

    resident_obj = resident
    if resident_obj is None:
        resident_obj = (
            Resident.objects.filter(
                tenant_id=session.tenant_id,
                phone_number=phone,
                market__isnull=False,
                is_anonymized=False,
                is_active=True,
            )
            .select_related("market")
            .first()
        )
    if resident_obj is None:
        return False

    if not session.is_bot_active:
        resume_bot(session)

    cart = get_or_create_open_cart(resident_obj)
    session.active_cart = cart
    session.temporary_name = ""
    session.pending_product = None
    session.state = ChatSession.State.PRODUCT_SEARCH
    session.save(
        update_fields=[
            "active_cart",
            "temporary_name",
            "pending_product",
            "state",
            "updated_at",
        ],
    )
    send_whatsapp_reply(
        instance,
        phone,
        HUMAN_QUEUE_PURCHASE_ESCAPE_MESSAGE,
        session=session,
    )
    append_assistant_message(session, HUMAN_QUEUE_PURCHASE_ESCAPE_MESSAGE)
    logger.info(
        "escape human queue for purchase tenant=%s phone=%s",
        session.tenant_id,
        phone,
    )
    return True

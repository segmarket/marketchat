"""Roteamento de mensagens no estado ACTIVE_BOT (gatekeeper + respostas)."""

from __future__ import annotations

import logging

from apps.chatbot.services.chat_history import append_assistant_message
from apps.chatbot.services.chatbot_core import (
    STATIC_COMPLAINT_ASSISTANT,
    STATIC_GENERAL_ASSISTANT,
    ChatbotCoreError,
    complete_with_session_history,
)
from apps.integrations.models import WhatsappInstance
from apps.residents.models import ChatSession, Resident
from apps.residents.services.whatsapp_reply import send_whatsapp_reply
from apps.sales.services.cart_repository import get_or_create_open_cart
from apps.sales.services.intent_gatekeeper import (
    COMPLAINT,
    GENERAL,
    MAINTENANCE_ISSUE,
    PAYMENT_ERROR,
    PURCHASE,
    STOCK_ISSUE,
    classify_user_intent,
)
from apps.notifications.services import create_critical_panel_notification
from apps.sales.services.owner_alert import (
    SUPPORT_RESIDENT_MESSAGE,
    notify_owner_support_issue,
)
from apps.sales.services.stock_issue_handler import handle_stock_issue_report
from apps.sales.services.resident_ai_context import (
    build_complaint_dynamic_context,
    build_payment_error_recovery_message,
    build_resident_dynamic_context,
    resident_display_name,
    resident_market_name,
)
from apps.tenants.models import Tenant

logger = logging.getLogger(__name__)


def _tenant_display_name(tenant_id: int) -> str:
    try:
        return (Tenant.objects.get(pk=tenant_id).name or "").strip() or "seu mercado"
    except Tenant.DoesNotExist:
        return "seu mercado"


def handle_maintenance_issue(
    *,
    instance: WhatsappInstance,
    tenant_id: int,
    phone: str,
    resident: Resident,
    session: ChatSession,
    message: str,
) -> bool:
    send_whatsapp_reply(instance, phone, SUPPORT_RESIDENT_MESSAGE)
    append_assistant_message(session, SUPPORT_RESIDENT_MESSAGE)
    notify_owner_support_issue(
        instance=instance,
        tenant_id=tenant_id,
        resident=resident,
        original_message=message,
        issue_label="Manutenção",
    )
    create_critical_panel_notification(
        tenant_id=tenant_id,
        resident=resident,
        intent_type=MAINTENANCE_ISSUE,
        original_message=message,
    )
    return True


def handle_payment_error_pivot(
    *,
    instance: WhatsappInstance,
    tenant_id: int,
    phone: str,
    resident: Resident,
    session: ChatSession,
    message: str,
) -> bool:
    """Registra chamado ao dono e oferece compra via Pix no WhatsApp."""
    notify_owner_support_issue(
        instance=instance,
        tenant_id=tenant_id,
        resident=resident,
        original_message=message,
        issue_label="Pagamento",
    )
    create_critical_panel_notification(
        tenant_id=tenant_id,
        resident=resident,
        intent_type=PAYMENT_ERROR,
        original_message=message,
    )

    recovery_text = build_payment_error_recovery_message(resident)
    send_whatsapp_reply(instance, phone, recovery_text)
    append_assistant_message(session, recovery_text)

    cart = get_or_create_open_cart(resident)
    session.active_cart = cart
    session.temporary_name = ""
    session.pending_product = None
    session.state = ChatSession.State.AWAITING_PRODUCT_SELECTION
    session.save(
        update_fields=[
            "active_cart",
            "temporary_name",
            "pending_product",
            "state",
            "updated_at",
        ],
    )
    return True


def handle_stock_issue(
    *,
    instance: WhatsappInstance,
    tenant_id: int,
    phone: str,
    resident: Resident,
    session: ChatSession,
    message: str,
) -> bool:
    handle_stock_issue_report(
        instance=instance,
        resident=resident,
        phone=phone,
        message=message,
    )
    return True


def handle_complaint(
    *,
    instance: WhatsappInstance,
    tenant_id: int,
    phone: str,
    resident: Resident,
    session: ChatSession,
    message: str,
) -> bool:
    """Reclamação: registra alerta ao dono e responde via ChatGPT com contexto de reclamação."""
    notify_owner_support_issue(
        instance=instance,
        tenant_id=tenant_id,
        resident=resident,
        original_message=message,
        issue_label="Reclamação",
    )

    dynamic_tail = (
        f"Empresa do mercado: {_tenant_display_name(tenant_id)}.\n"
        f"{build_complaint_dynamic_context(resident)}"
    )
    try:
        reply = complete_with_session_history(
            session=session,
            static_system=STATIC_COMPLAINT_ASSISTANT,
            user_content=message,
            dynamic_system_tail=dynamic_tail,
            max_tokens=100,
        )
    except ChatbotCoreError:
        reply = (
            "Sinto muito pelo transtorno. Pode me contar com mais detalhes o que aconteceu? "
            "Já avisei a equipe responsável pelo mercado."
        )
        append_assistant_message(session, reply)
    except Exception:
        logger.exception("Falha na resposta de reclamação")
        reply = (
            "Recebi sua reclamação e já encaminhei para a equipe do mercado. "
            "Pode descrever melhor o que aconteceu?"
        )
        append_assistant_message(session, reply)

    if reply:
        send_whatsapp_reply(
            instance,
            phone,
            reply,
            intent_type=COMPLAINT,
            session=session,
        )
    return True


def handle_general_message(
    *,
    instance: WhatsappInstance,
    tenant_id: int,
    phone: str,
    resident: Resident,
    session: ChatSession,
    message: str,
) -> bool:
    dynamic_tail = (
        f"Empresa do mercado: {_tenant_display_name(tenant_id)}.\n"
        f"{build_resident_dynamic_context(resident)}"
    )
    try:
        reply = complete_with_session_history(
            session=session,
            static_system=STATIC_GENERAL_ASSISTANT,
            user_content=message,
            dynamic_system_tail=dynamic_tail,
            max_tokens=80,
        )
    except ChatbotCoreError:
        reply = (
            "Obrigado pela mensagem! Em instantes um atendente pode te ajudar melhor."
        )
        append_assistant_message(session, reply)
    except Exception:
        logger.exception("Falha na resposta geral")
        name = resident_display_name(resident)
        market = resident_market_name(resident)
        reply = f"Olá, {name}! Como posso te ajudar hoje aqui no mercado do {market}?"
        append_assistant_message(session, reply)

    if reply:
        send_whatsapp_reply(instance, phone, reply)
    return True


def route_active_bot_message(
    *,
    tenant_id: int,
    instance: WhatsappInstance,
    phone: str,
    resident: Resident,
    session: ChatSession,
    message: str,
    on_purchase,
) -> bool:
    """
    Gatekeeper: classifica intenção e roteia.
    on_purchase: callable() -> bool executado apenas se intenção for PURCHASE.
    """
    intent = classify_user_intent(message)

    if intent == PURCHASE:
        return on_purchase()

    if intent == MAINTENANCE_ISSUE:
        return handle_maintenance_issue(
            instance=instance,
            tenant_id=tenant_id,
            phone=phone,
            resident=resident,
            session=session,
            message=message,
        )

    if intent == COMPLAINT:
        return handle_complaint(
            instance=instance,
            tenant_id=tenant_id,
            phone=phone,
            resident=resident,
            session=session,
            message=message,
        )

    if intent == PAYMENT_ERROR:
        return handle_payment_error_pivot(
            instance=instance,
            tenant_id=tenant_id,
            phone=phone,
            resident=resident,
            session=session,
            message=message,
        )

    if intent == STOCK_ISSUE:
        return handle_stock_issue(
            instance=instance,
            tenant_id=tenant_id,
            phone=phone,
            resident=resident,
            session=session,
            message=message,
        )

    return handle_general_message(
        instance=instance,
        tenant_id=tenant_id,
        phone=phone,
        resident=resident,
        session=session,
        message=message,
    )

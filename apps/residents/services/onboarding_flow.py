from __future__ import annotations

import logging

from apps.integrations.models import WhatsappInstance
from apps.residents.models import ChatSession, Resident
from apps.sales.services.resident_ai_context import resident_first_name_from_string
from apps.residents.services.condo_match import find_market_by_query
from apps.residents.services.greeting import greeting_for_now
from apps.residents.services.whatsapp_reply import send_whatsapp_reply

logger = logging.getLogger(__name__)

REJECT_CONDO_MESSAGE = (
    "Infelizmente não temos mercados parceiros cadastrados neste condomínio."
)


def resident_has_completed_onboarding(tenant_id: int, phone: str) -> bool:
    return Resident.objects.filter(
        tenant_id=tenant_id,
        phone_number=phone,
        market__isnull=False,
    ).exists()


def process_inbound_message(
    tenant_id: int,
    instance: WhatsappInstance,
    phone: str,
    text: str,
) -> bool:
    """
    Processa mensagem no fluxo de onboarding.
    Retorna True se a mensagem foi tratada pelo onboarding; False se deve ir ao bot.
    """
    if resident_has_completed_onboarding(tenant_id, phone):
        return False

    message = (text or "").strip()
    if not message:
        return True

    session = ChatSession.objects.filter(
        tenant_id=tenant_id,
        phone_number=phone,
    ).first()

    onboarding_states = (
        ChatSession.State.AWAITING_NAME,
        ChatSession.State.AWAITING_CONDO,
    )
    # O webhook cria ChatSession com ACTIVE_BOT antes do onboarding; sem isso o fluxo
    # cai no return final e o contato novo não recebe resposta.
    if session is None or session.state not in onboarding_states:
        _start_onboarding(instance, phone, tenant_id)
        return True

    if session.state == ChatSession.State.AWAITING_NAME:
        _handle_awaiting_name(instance, session, message)
        return True

    if session.state == ChatSession.State.AWAITING_CONDO:
        _handle_awaiting_condo(instance, session, tenant_id, phone, message)
        return True

    return True


def _start_onboarding(instance: WhatsappInstance, phone: str, tenant_id: int) -> None:
    greeting = greeting_for_now()
    send_whatsapp_reply(
        instance,
        phone,
        f"{greeting}! Seja bem-vindo ao assistente virtual do seu mercado autônomo. "
        "Para começarmos seu atendimento, por favor, nos diga seu Nome Completo:",
    )
    ChatSession.objects.update_or_create(
        tenant_id=tenant_id,
        phone_number=phone,
        defaults={
            "state": ChatSession.State.AWAITING_NAME,
            "temporary_name": "",
        },
    )


def _handle_awaiting_name(
    instance: WhatsappInstance,
    session: ChatSession,
    message: str,
) -> None:
    name = message.strip()
    if not name:
        send_whatsapp_reply(
            instance,
            session.phone_number,
            "Por favor, informe seu nome completo para continuarmos.",
        )
        return

    session.temporary_name = name
    session.state = ChatSession.State.AWAITING_CONDO
    session.save(update_fields=["temporary_name", "state", "updated_at"])

    primeiro_nome = resident_first_name_from_string(name)
    send_whatsapp_reply(
        instance,
        session.phone_number,
        f"Prazer em te conhecer, {primeiro_nome}! Agora, digite o Nome do seu Condomínio "
        "para localizarmos sua unidade:",
    )


def _handle_awaiting_condo(
    instance: WhatsappInstance,
    session: ChatSession,
    tenant_id: int,
    phone: str,
    message: str,
) -> None:
    market = find_market_by_query(tenant_id, message)
    if market is None:
        send_whatsapp_reply(instance, phone, REJECT_CONDO_MESSAGE)
        return

    name = session.temporary_name.strip()
    Resident.objects.update_or_create(
        tenant_id=tenant_id,
        phone_number=phone,
        defaults={
            "name": name,
            "market": market,
        },
    )
    session.state = ChatSession.State.IDLE
    session.temporary_name = ""
    session.active_cart = None
    session.pending_product = None
    session.save(
        update_fields=[
            "state",
            "temporary_name",
            "active_cart",
            "pending_product",
            "updated_at",
        ],
    )

    send_whatsapp_reply(
        instance,
        phone,
        f"Perfeito, identificamos o mercado no {market.name}! "
        "Seu cadastro foi concluído com sucesso. Como posso te ajudar agora?",
    )
    logger.info(
        "Morador cadastrado: tenant=%s phone=%s market=%s",
        tenant_id,
        phone,
        market.id,
    )

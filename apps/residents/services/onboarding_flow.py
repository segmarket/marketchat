from __future__ import annotations

import logging
import re

from django.conf import settings

from apps.core.pii import mask_phone
from apps.integrations.models import WhatsappInstance
from apps.markets.models import Market
from apps.residents.models import ChatSession, Resident
from apps.residents.services.condo_match import find_market_by_query
from apps.residents.services.greeting import greeting_for_now
from apps.residents.services.onboarding_ai import (
    NON_CACHEABLE_INTENTS,
    OnboardingAIResult,
    analyze_onboarding_message,
)
from apps.residents.services.whatsapp_reply import send_whatsapp_reply
from apps.sales.services.resident_ai_context import resident_first_name_from_string

logger = logging.getLogger(__name__)

REJECT_CONDO_MESSAGE = (
    "Infelizmente não encontrei nenhum condomínio parceiro com esse nome. "
    "Você pode verificar se digitou corretamente?"
)

ASK_NAME_MESSAGE = "Qual o seu nome?"

ONBOARDING_RESUME_INTENT_MESSAGE = (
    "Cadastro concluído! Retomando o assunto do seu primeiro contato..."
)

DEFAULT_HUMAN_TRANSFER_MESSAGE = (
    "Entendi que você precisa de um atendimento mais detalhado. "
    "Vou pausar o assistente virtual e transferir para a nossa equipe humana. "
    "Aguarde um instante!"
)

_ONBOARDING_STATES = (
    ChatSession.State.AWAITING_NAME,
    ChatSession.State.AWAITING_CONDO,
)


def _resolve_pending_intent(existing: str, new_intent: str) -> str:
    """Preserva reclamacao/maquininha entre turns; não cacheia spam/áudio/humano."""
    current = (existing or "").strip()
    incoming = (new_intent or "").strip()
    if incoming in NON_CACHEABLE_INTENTS:
        return current
    if incoming == "reclamacao":
        return "reclamacao"
    if incoming == "problema_maquininha":
        return "problema_maquininha"
    if not current and incoming:
        return incoming
    return current


def resident_has_completed_onboarding(tenant_id: int, phone: str) -> bool:
    return Resident.objects.filter(
        tenant_id=tenant_id,
        phone_number=phone,
        market__isnull=False,
        is_anonymized=False,
        is_active=True,
    ).exists()


def build_onboarding_privacy_message() -> str:
    """Aviso LGPD + consentimento (sem pedido de nome)."""
    privacy_url = f"{settings.MARKETING_PUBLIC_ORIGIN.rstrip('/')}/privacidade"
    greeting = greeting_for_now()
    return (
        f"👋 {greeting}! Sou o assistente virtual do mercado. "
        "Para fazer compras e garantir sua segurança, processamos seus dados conforme nossa "
        f"Política de Privacidade: {privacy_url}. "
        "Ao continuar e enviar sua lista, você concorda com nossos termos."
    )


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

    if session is not None:
        from apps.chatbot.services.human_handover import should_mute_for_human
        from apps.sales.services.maquininha_backup import (
            try_escape_human_queue_for_purchase,
        )

        if should_mute_for_human(session):
            if try_escape_human_queue_for_purchase(
                instance=instance,
                phone=phone,
                text=message,
                session=session,
            ):
                return True
            logger.info(
                "onboarding mute humano tenant=%s phone=%s state=%s bot_active=%s",
                tenant_id,
                mask_phone(phone),
                session.state,
                session.is_bot_active,
            )
            return True

    is_first_contact = session is None or session.state not in _ONBOARDING_STATES
    _process_onboarding_ai_turn(
        instance=instance,
        phone=phone,
        tenant_id=tenant_id,
        message=message,
        session=session,
        is_first_contact=is_first_contact,
    )
    return True


def _process_onboarding_ai_turn(
    *,
    instance: WhatsappInstance,
    phone: str,
    tenant_id: int,
    message: str,
    session: ChatSession | None,
    is_first_contact: bool,
) -> None:
    known_name = (session.temporary_name or "").strip() if session else ""
    if session and session.state == ChatSession.State.AWAITING_CONDO and known_name:
        missing = "condominio"
    elif known_name:
        missing = "condominio"
    else:
        missing = "ambos"

    result = analyze_onboarding_message(
        message,
        known_name=known_name or None,
        known_condo=None,
        missing=missing,
    )
    if result is None:
        _fallback_onboarding_turn(
            instance=instance,
            phone=phone,
            tenant_id=tenant_id,
            message=message,
            session=session,
            is_first_contact=is_first_contact,
            known_name=known_name,
        )
        return

    acao = result.acao_imediata_codigo

    if acao == "ignorar_mensagem":
        logger.info(
            "onboarding: mensagem ignorada (spam/vendas) tenant=%s phone=%s",
            tenant_id,
            mask_phone(phone),
        )
        return

    if acao == "pausar_bot_transferir":
        _transfer_to_human(
            instance=instance,
            phone=phone,
            tenant_id=tenant_id,
            session=session,
            reply_text=result.resposta_texto,
        )
        return

    if acao == "iniciar_venda_backup":
        _handle_iniciar_venda_backup(
            instance=instance,
            phone=phone,
            tenant_id=tenant_id,
            message=message,
            session=session,
            result=result,
            known_name=known_name,
            is_first_contact=is_first_contact,
        )
        return

    # continuar_onboarding
    nome = result.nome or known_name or None
    market: Market | None = None
    condo_query = result.condominio
    if condo_query:
        market = find_market_by_query(tenant_id, condo_query)

    existing_intent = (session.pending_intent or "").strip() if session else ""
    pending_intent = _resolve_pending_intent(
        existing_intent,
        result.intencao_primaria,
    )

    # Completo: nome + condo casado — sem resposta_texto da IA
    if nome and market is not None:
        if is_first_contact:
            send_whatsapp_reply(instance, phone, build_onboarding_privacy_message())
        session_obj, _ = ChatSession.objects.update_or_create(
            tenant_id=tenant_id,
            phone_number=phone,
            defaults={
                "temporary_name": nome,
                "pending_intent": pending_intent,
                "state": ChatSession.State.AWAITING_CONDO,
            },
        )
        session_obj.pending_intent = pending_intent
        _complete_onboarding_with_market(
            instance=instance,
            session=session_obj,
            tenant_id=tenant_id,
            phone=phone,
            name=nome,
            market=market,
        )
        return

    # Parcial
    if is_first_contact:
        send_whatsapp_reply(instance, phone, build_onboarding_privacy_message())

    if condo_query and market is None:
        send_whatsapp_reply(instance, phone, REJECT_CONDO_MESSAGE)
        next_state = (
            ChatSession.State.AWAITING_CONDO
            if nome
            else ChatSession.State.AWAITING_NAME
        )
        ChatSession.objects.update_or_create(
            tenant_id=tenant_id,
            phone_number=phone,
            defaults={
                "temporary_name": nome or "",
                "pending_intent": pending_intent,
                "state": next_state,
            },
        )
        return

    if result.resposta_texto:
        send_whatsapp_reply(instance, phone, result.resposta_texto)

    if nome:
        ChatSession.objects.update_or_create(
            tenant_id=tenant_id,
            phone_number=phone,
            defaults={
                "temporary_name": nome,
                "pending_intent": pending_intent,
                "state": ChatSession.State.AWAITING_CONDO,
            },
        )
    else:
        ChatSession.objects.update_or_create(
            tenant_id=tenant_id,
            phone_number=phone,
            defaults={
                "temporary_name": known_name or "",
                "pending_intent": pending_intent,
                "state": ChatSession.State.AWAITING_NAME,
            },
        )


def _handle_iniciar_venda_backup(
    *,
    instance: WhatsappInstance,
    phone: str,
    tenant_id: int,
    message: str,
    session: ChatSession | None,
    result: OnboardingAIResult,
    known_name: str,
    is_first_contact: bool,
) -> None:
    """Maquininha fora: se já cadastrado, vende via Pix; senão guarda intent e cadastra."""
    from apps.sales.services.maquininha_backup import start_maquininha_backup_sale

    resident = (
        Resident.objects.filter(
            tenant_id=tenant_id,
            phone_number=phone,
            market__isnull=False,
            is_anonymized=False,
            is_active=True,
        )
        .select_related("market")
        .first()
    )
    if resident is not None:
        session_obj = session
        if session_obj is None:
            session_obj, _ = ChatSession.objects.get_or_create(
                tenant_id=tenant_id,
                phone_number=phone,
            )
        start_maquininha_backup_sale(
            instance=instance,
            tenant_id=tenant_id,
            phone=phone,
            resident=resident,
            session=session_obj,
            message=message,
        )
        return

    # Ainda sem cadastro completo: preservar intent e seguir onboarding.
    nome = result.nome or known_name or None
    market: Market | None = None
    condo_query = result.condominio
    if condo_query:
        market = find_market_by_query(tenant_id, condo_query)

    existing_intent = (session.pending_intent or "").strip() if session else ""
    pending_intent = _resolve_pending_intent(existing_intent, "problema_maquininha")

    if nome and market is not None:
        if is_first_contact:
            send_whatsapp_reply(instance, phone, build_onboarding_privacy_message())
        session_obj, _ = ChatSession.objects.update_or_create(
            tenant_id=tenant_id,
            phone_number=phone,
            defaults={
                "temporary_name": nome,
                "pending_intent": pending_intent,
                "state": ChatSession.State.AWAITING_CONDO,
            },
        )
        session_obj.pending_intent = pending_intent
        _complete_onboarding_with_market(
            instance=instance,
            session=session_obj,
            tenant_id=tenant_id,
            phone=phone,
            name=nome,
            market=market,
        )
        return

    if is_first_contact:
        send_whatsapp_reply(instance, phone, build_onboarding_privacy_message())

    if condo_query and market is None:
        send_whatsapp_reply(instance, phone, REJECT_CONDO_MESSAGE)
        next_state = (
            ChatSession.State.AWAITING_CONDO
            if nome
            else ChatSession.State.AWAITING_NAME
        )
        ChatSession.objects.update_or_create(
            tenant_id=tenant_id,
            phone_number=phone,
            defaults={
                "temporary_name": nome or "",
                "pending_intent": pending_intent,
                "state": next_state,
            },
        )
        return

    ask = (
        result.resposta_texto
        or (
            f"Prazer{(', ' + nome) if nome else ''}! Vi o problema na maquininha — "
            "já vamos te ajudar a comprar por aqui. "
            + (
                "Qual o nome do seu condomínio?"
                if nome
                else "Qual o seu nome?"
            )
        )
    )
    send_whatsapp_reply(instance, phone, ask)
    if nome:
        ChatSession.objects.update_or_create(
            tenant_id=tenant_id,
            phone_number=phone,
            defaults={
                "temporary_name": nome,
                "pending_intent": pending_intent,
                "state": ChatSession.State.AWAITING_CONDO,
            },
        )
    else:
        ChatSession.objects.update_or_create(
            tenant_id=tenant_id,
            phone_number=phone,
            defaults={
                "temporary_name": known_name or "",
                "pending_intent": pending_intent,
                "state": ChatSession.State.AWAITING_NAME,
            },
        )


def _transfer_to_human(
    *,
    instance: WhatsappInstance,
    phone: str,
    tenant_id: int,
    session: ChatSession | None,
    reply_text: str,
) -> None:
    from apps.chatbot.services.human_handover import pause_bot
    from apps.sales.services.chat_fsm import transition

    session_obj, _ = ChatSession.objects.update_or_create(
        tenant_id=tenant_id,
        phone_number=phone,
        defaults={
            "state": ChatSession.State.WAITING_FOR_HUMAN,
            "temporary_name": (session.temporary_name if session else "") or "",
            "pending_intent": (session.pending_intent if session else "") or "",
        },
    )
    pause_bot(session_obj)
    transition(
        session_obj,
        ChatSession.State.WAITING_FOR_HUMAN,
        reason="onboarding_human_transfer",
    )
    body = (reply_text or "").strip() or DEFAULT_HUMAN_TRANSFER_MESSAGE
    send_whatsapp_reply(instance, phone, body, session=session_obj)
    logger.info(
        "onboarding: transferido para humano tenant=%s phone=%s",
        tenant_id,
        mask_phone(phone),
    )


def _is_acceptable_fallback_name(message: str) -> bool:
    """Aceita nome curto no fallback; rejeita frases/perguntas."""
    text = (message or "").strip()
    if not text or len(text) > 40 or "?" in text:
        return False
    tokens = [t for t in re.split(r"\s+", text) if t]
    if not tokens or len(tokens) > 3:
        return False
    greetings = {"oi", "olá", "ola", "opa", "eae", "hey", "bom", "boa"}
    if len(tokens) == 1 and tokens[0].lower().strip(".,!") in greetings:
        return False
    return True


def _fallback_onboarding_turn(
    *,
    instance: WhatsappInstance,
    phone: str,
    tenant_id: int,
    message: str,
    session: ChatSession | None,
    is_first_contact: bool,
    known_name: str,
) -> None:
    if is_first_contact:
        _start_onboarding(instance, phone, tenant_id)
        return

    if session and session.state == ChatSession.State.AWAITING_NAME:
        if _is_acceptable_fallback_name(message):
            session.temporary_name = message.strip()
            session.state = ChatSession.State.AWAITING_CONDO
            session.save(update_fields=["temporary_name", "state", "updated_at"])
            primeiro = resident_first_name_from_string(message.strip())
            send_whatsapp_reply(
                instance,
                phone,
                f"Prazer em te conhecer, {primeiro}! Agora, digite o nome do seu "
                "condomínio para localizarmos sua unidade:",
            )
        else:
            send_whatsapp_reply(
                instance,
                phone,
                "Não consegui identificar como te chamar. Pode me dizer só o seu nome?",
            )
        return

    if session and session.state == ChatSession.State.AWAITING_CONDO:
        market = find_market_by_query(tenant_id, message)
        if market is None:
            send_whatsapp_reply(instance, phone, REJECT_CONDO_MESSAGE)
            return
        name = known_name or session.temporary_name.strip()
        if not name:
            send_whatsapp_reply(instance, phone, ASK_NAME_MESSAGE)
            session.state = ChatSession.State.AWAITING_NAME
            session.save(update_fields=["state", "updated_at"])
            return
        _complete_onboarding_with_market(
            instance=instance,
            session=session,
            tenant_id=tenant_id,
            phone=phone,
            name=name,
            market=market,
        )
        return

    _start_onboarding(instance, phone, tenant_id)


def _start_onboarding(
    instance: WhatsappInstance,
    phone: str,
    tenant_id: int,
) -> None:
    """Fluxo rígido: privacidade + pedido de nome."""
    send_whatsapp_reply(
        instance,
        phone,
        f"{build_onboarding_privacy_message()}\n\n{ASK_NAME_MESSAGE}",
    )
    ChatSession.objects.update_or_create(
        tenant_id=tenant_id,
        phone_number=phone,
        defaults={
            "state": ChatSession.State.AWAITING_NAME,
            "temporary_name": "",
        },
    )


def _complete_onboarding_with_market(
    *,
    instance: WhatsappInstance,
    session: ChatSession,
    tenant_id: int,
    phone: str,
    name: str,
    market: Market,
) -> None:
    resident, _created = Resident.objects.update_or_create(
        tenant_id=tenant_id,
        phone_number=phone,
        defaults={
            "name": name,
            "market": market,
        },
    )
    intent = (session.pending_intent or "").strip()
    session.temporary_name = ""
    session.pending_intent = ""
    session.active_cart = None
    session.pending_product = None
    session.save(
        update_fields=[
            "temporary_name",
            "pending_intent",
            "active_cart",
            "pending_product",
            "updated_at",
        ],
    )

    completion_intro = (
        f"Perfeito, identificamos o mercado no {market.name}!\n"
        "Seu cadastro foi concluído com sucesso."
    )

    if intent == "reclamacao":
        from apps.sales.services.main_menu import start_support_details_collection
        from apps.sales.services.whatsapp_interactive import MENU_PRODUCT

        send_whatsapp_reply(
            instance,
            phone,
            f"{completion_intro}\n\n{ONBOARDING_RESUME_INTENT_MESSAGE}",
            session=session,
        )
        start_support_details_collection(
            instance=instance,
            phone=phone,
            session=session,
            choice=MENU_PRODUCT,
            reason="onboarding_resume_product_issue",
        )
    elif intent == "problema_maquininha":
        from apps.sales.services.maquininha_backup import start_maquininha_backup_sale

        send_whatsapp_reply(
            instance,
            phone,
            f"{completion_intro}\n\n{ONBOARDING_RESUME_INTENT_MESSAGE}",
            session=session,
        )
        start_maquininha_backup_sale(
            instance=instance,
            tenant_id=tenant_id,
            phone=phone,
            resident=resident,
            session=session,
            message="",
            notify=True,
        )
    else:
        from apps.sales.services.main_menu import show_main_menu

        show_main_menu(
            instance=instance,
            phone=phone,
            resident=resident,
            session=session,
            intro=completion_intro,
            reason="onboarding_complete",
        )
    logger.info(
        "Morador cadastrado: tenant=%s phone=%s market=%s intent=%s",
        tenant_id,
        mask_phone(phone),
        market.id,
        intent or "-",
    )

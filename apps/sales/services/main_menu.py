"""Menu principal interativo após saudação (GREETING)."""

from __future__ import annotations

import logging
import re
import unicodedata

from apps.chatbot.services.chat_logging import log_outbound
from apps.integrations.models import WhatsappInstance
from apps.residents.models import ChatSession, Resident
from apps.residents.services.whatsapp_reply import send_whatsapp_reply
from apps.sales.services.cart_repository import get_or_create_open_cart
from apps.sales.services.chat_fsm import transition
from apps.sales.services.intent_gatekeeper import is_opening_greeting
from apps.sales.services.product_search import MAIN_MENU_PURCHASE_PROMPT
from apps.sales.services.resident_ai_context import resident_display_name
from apps.sales.services.whatsapp_interactive import (
    MAIN_MENU_ROW_IDS,
    MAIN_MENU_ROWS,
    MENU_BILLING,
    MENU_FRIDGE,
    MENU_OTHER,
    MENU_PAYMENT,
    MENU_PRODUCT,
    MENU_PURCHASE,
    MENU_STOCK,
    MENU_STORE,
    MENU_SUGGEST,
    MENU_UNCATALOGUED,
    build_main_menu_text_fallback,
    send_main_menu_list,
)

logger = logging.getLogger(__name__)

_MENU_NUMBER_WORDS = {
    "um": 1,
    "uma": 1,
    "dois": 2,
    "duas": 2,
    "tres": 3,
    "quatro": 4,
    "cinco": 5,
    "seis": 6,
    "sete": 7,
    "oito": 8,
    "nove": 9,
    "dez": 10,
}

_OPTION_HINTS: tuple[tuple[str, tuple[str, ...]], ...] = (
    (MENU_PURCHASE, ("comprar", "quero comprar", "buscar produto", "fazer uma compra")),
    (MENU_SUGGEST, ("sugestao", "sugerir produto", "quero que vendam")),
    (MENU_STOCK, ("falta de", "sem estoque", "acabou")),
    (MENU_UNCATALOGUED, ("sem cadastro", "sem preco", "nao cadastrado")),
    (MENU_PAYMENT, ("maquininha", "indisp", "pix nao funciona")),
    (MENU_BILLING, ("cobranca", "valor errado", "cobrado")),
    (MENU_FRIDGE, ("geladeira", "freezer")),
    (MENU_STORE, ("problema loja", "loja")),
    (MENU_PRODUCT, ("produto estragado", "vencido", "problema com produto")),
    (MENU_OTHER, ("outros", "outro assunto")),
)


def _normalize_choice_text(text: str) -> str:
    lowered = (text or "").strip().lower()
    decomposed = unicodedata.normalize("NFD", lowered)
    return "".join(c for c in decomposed if unicodedata.category(c) != "Mn")


def build_main_menu_greeting(*, resident: Resident) -> str:
    name = resident_display_name(resident)
    return f"Olá, {name}! Como posso ajudar?"


def build_main_menu_message(*, resident: Resident) -> str:
    """Texto completo do menu (inbox + fallback quando a lista falha)."""
    return build_main_menu_text_fallback(greeting=build_main_menu_greeting(resident=resident))


def build_main_menu_reminder() -> str:
    lines = ["Não entendi. Escolha uma opção:"]
    for idx, (_row_id, title, _desc) in enumerate(MAIN_MENU_ROWS, start=1):
        lines.append(f"{idx} — {title}")
    return "\n".join(lines)


def build_maintenance_prompt() -> str:
    return (
        "Descreva em texto o problema (maquininha, geladeira, etc.) "
        "que vamos registrar."
    )


def build_stock_prompt() -> str:
    return "Conte em texto sobre o produto (falta, dúvida ou preço)."


def build_uncatalogued_prompt() -> str:
    return (
        "Qual produto está sem cadastro ou sem preço? "
        "Informe o nome ou a marca que vamos registrar."
    )


def build_payment_prompt() -> str:
    return (
        "Descreva o problema de pagamento (maquininha, Pix indisponível, etc.)."
    )


def build_billing_prompt() -> str:
    return "Conte o que aconteceu com a cobrança (valor, duplicidade, etc.)."


def build_fridge_prompt() -> str:
    return "Descreva o problema na geladeira ou freezer."


def build_store_prompt() -> str:
    return "Descreva o problema na loja (iluminação, porta, limpeza, etc.)."


def build_product_issue_prompt() -> str:
    return (
        "Descreva o problema com o produto (estragado, vencido, embalagem, etc.)."
    )


def build_other_prompt() -> str:
    return "Como posso ajudar? Descreva em texto o que você precisa."


def build_suggest_prompt() -> str:
    return (
        "Qual produto você gostaria de sugerir para o mercado? "
        "Pode informar o nome ou a marca."
    )


def parse_main_menu_choice(
    text: str = "",
    *,
    interactive_id: str = "",
) -> str | None:
    """Retorna rowId `menu:*` ou None se não reconhecer."""
    row_id = (interactive_id or "").strip()
    if row_id in MAIN_MENU_ROW_IDS:
        return row_id

    raw = (text or "").strip()
    if not raw:
        return None

    digit_head = re.match(r"^(10|[1-9])", raw)
    if digit_head:
        rest = raw[digit_head.end() :]
        if not rest or re.fullmatch(r"[\ufe0f\u20e3\s]*", rest):
            return MAIN_MENU_ROWS[int(digit_head.group(1)) - 1][0]

    normalized = _normalize_choice_text(raw)
    if re.fullmatch(r"10|[1-9]", normalized):
        idx = int(normalized)
        return MAIN_MENU_ROWS[idx - 1][0]

    digit_match = re.search(r"\b(10|[1-9])\b", normalized)
    if digit_match:
        idx = int(digit_match.group(1))
        return MAIN_MENU_ROWS[idx - 1][0]

    if normalized in _MENU_NUMBER_WORDS:
        idx = _MENU_NUMBER_WORDS[normalized]
        if 1 <= idx <= len(MAIN_MENU_ROWS):
            return MAIN_MENU_ROWS[idx - 1][0]

    option_match = re.match(r"^(?:opcao|opção)\s*(10|[1-9])\b", normalized)
    if option_match:
        idx = int(option_match.group(1))
        return MAIN_MENU_ROWS[idx - 1][0]

    for menu_id, keywords in _OPTION_HINTS:
        if any(keyword in normalized for keyword in keywords):
            return menu_id

    return None


def show_main_menu(
    *,
    instance: WhatsappInstance,
    phone: str,
    resident: Resident,
    session: ChatSession,
) -> None:
    transition(session, ChatSession.State.AWAITING_MAIN_MENU, reason="greeting_menu")
    greeting = build_main_menu_greeting(resident=resident)
    menu_text = build_main_menu_message(resident=resident)

    sent_list = send_main_menu_list(
        instance,
        phone,
        title="Atendimento",
        description=greeting,
    )
    if sent_list:
        log_outbound(
            instance=instance,
            phone=phone,
            message_text=menu_text,
            session=session,
        )
        return

    send_whatsapp_reply(instance, phone, menu_text, session=session)


def _prompt_then_idle(
    *,
    instance: WhatsappInstance,
    phone: str,
    session: ChatSession,
    reason: str,
    prompt: str,
) -> None:
    transition(session, ChatSession.State.IDLE, reason=reason)
    send_whatsapp_reply(instance, phone, prompt, session=session)


def handle_main_menu_message(
    *,
    instance: WhatsappInstance,
    phone: str,
    resident: Resident,
    session: ChatSession,
    text: str = "",
    interactive_id: str = "",
) -> bool:
    """Processa escolha no menu principal. Retorna True se tratou."""
    if session.state != ChatSession.State.AWAITING_MAIN_MENU:
        return False

    choice = parse_main_menu_choice(text, interactive_id=interactive_id)
    if choice is None:
        if text and is_opening_greeting(text):
            return True
        send_whatsapp_reply(instance, phone, build_main_menu_reminder(), session=session)
        return True

    if choice == MENU_PURCHASE:
        cart = get_or_create_open_cart(resident)
        session.active_cart = cart
        session.save(update_fields=["active_cart", "updated_at"])
        transition(session, ChatSession.State.PRODUCT_SEARCH, reason="main_menu_purchase")
        send_whatsapp_reply(instance, phone, MAIN_MENU_PURCHASE_PROMPT, session=session)
        return True

    if choice == MENU_SUGGEST:
        transition(
            session,
            ChatSession.State.AWAITING_PRODUCT_SUGGESTION,
            reason="main_menu_suggest",
        )
        send_whatsapp_reply(instance, phone, build_suggest_prompt(), session=session)
        return True

    if choice == MENU_STOCK:
        _prompt_then_idle(
            instance=instance,
            phone=phone,
            session=session,
            reason="main_menu_stock",
            prompt=build_stock_prompt(),
        )
        return True

    if choice == MENU_UNCATALOGUED:
        _prompt_then_idle(
            instance=instance,
            phone=phone,
            session=session,
            reason="main_menu_uncatalogued",
            prompt=build_uncatalogued_prompt(),
        )
        return True

    if choice == MENU_PAYMENT:
        _prompt_then_idle(
            instance=instance,
            phone=phone,
            session=session,
            reason="main_menu_payment",
            prompt=build_payment_prompt(),
        )
        return True

    if choice == MENU_BILLING:
        _prompt_then_idle(
            instance=instance,
            phone=phone,
            session=session,
            reason="main_menu_billing",
            prompt=build_billing_prompt(),
        )
        return True

    if choice == MENU_FRIDGE:
        _prompt_then_idle(
            instance=instance,
            phone=phone,
            session=session,
            reason="main_menu_fridge",
            prompt=build_fridge_prompt(),
        )
        return True

    if choice == MENU_STORE:
        _prompt_then_idle(
            instance=instance,
            phone=phone,
            session=session,
            reason="main_menu_store",
            prompt=build_store_prompt(),
        )
        return True

    if choice == MENU_PRODUCT:
        _prompt_then_idle(
            instance=instance,
            phone=phone,
            session=session,
            reason="main_menu_product_issue",
            prompt=build_product_issue_prompt(),
        )
        return True

    if choice == MENU_OTHER:
        _prompt_then_idle(
            instance=instance,
            phone=phone,
            session=session,
            reason="main_menu_other",
            prompt=build_other_prompt(),
        )
        return True

    logger.warning("Menu choice sem handler: %s", choice)
    send_whatsapp_reply(instance, phone, build_main_menu_reminder(), session=session)
    return True

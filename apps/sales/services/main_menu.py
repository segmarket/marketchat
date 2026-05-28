"""Menu principal numérico após saudação (GREETING)."""

from __future__ import annotations

import re
import unicodedata

from apps.integrations.models import WhatsappInstance
from apps.residents.models import ChatSession, Resident
from apps.residents.services.whatsapp_reply import send_whatsapp_reply
from apps.sales.services.cart_repository import get_or_create_open_cart
from apps.sales.services.chat_fsm import reset_to_idle, transition
from apps.sales.services.product_search import MAIN_MENU_PURCHASE_PROMPT
from apps.sales.services.resident_ai_context import resident_display_name

_MENU_NUMBER_WORDS = {
    "um": 1,
    "uma": 1,
    "dois": 2,
    "duas": 2,
    "tres": 3,
    "quatro": 4,
}

_OPTION_HINTS = (
    (1, ("comprar", "quero comprar", "buscar produto")),
    (2, ("manutencao", "maquininha", "geladeira quebrada")),
    (3, ("falta de", "sem estoque", "duvida de preco")),
)


def _normalize_choice_text(text: str) -> str:
    lowered = (text or "").strip().lower()
    decomposed = unicodedata.normalize("NFD", lowered)
    return "".join(c for c in decomposed if unicodedata.category(c) != "Mn")


def build_main_menu_message(*, resident: Resident) -> str:
    name = resident_display_name(resident)
    return (
        f"Olá, {name}! Como posso ajudar?\n\n"
        "1️⃣ Fazer uma compra\n"
        "2️⃣ Reportar problema (maquininha, geladeira, etc.)\n"
        "3️⃣ Dúvida ou falta de produto\n"
        "4️⃣ Só passei para cumprimentar\n\n"
        "Responda com o número da opção (1 a 4)."
    )


def build_main_menu_reminder() -> str:
    return (
        "Não entendi. Escolha uma opção:\n"
        "1 — Comprar\n"
        "2 — Reportar problema\n"
        "3 — Dúvida ou estoque\n"
        "4 — Só cumprimentar"
    )


def build_main_menu_farewell(*, resident: Resident) -> str:
    name = resident_display_name(resident)
    return (
        f"Por nada, {name}! Qualquer coisa que precisar aqui no mercado, "
        "é só me chamar. Até mais! 👋"
    )


def build_maintenance_prompt() -> str:
    return (
        "Descreva em texto o problema (maquininha, geladeira, etc.) "
        "que vamos registrar."
    )


def build_stock_prompt() -> str:
    return (
        "Conte em texto sobre o produto (falta, dúvida ou preço)."
    )


def parse_main_menu_choice(text: str) -> int | None:
    """Retorna 1–4 ou None se não reconhecer."""
    raw = (text or "").strip()
    if not raw:
        return None

    if re.fullmatch(r"[1-4]️?", raw):
        return int(raw[0])

    normalized = _normalize_choice_text(raw)
    if re.fullmatch(r"[1-4]", normalized):
        return int(normalized)

    digit_match = re.search(r"\b([1-4])\b", normalized)
    if digit_match:
        return int(digit_match.group(1))

    if normalized in _MENU_NUMBER_WORDS:
        return _MENU_NUMBER_WORDS[normalized]

    option_match = re.match(r"^(?:opcao|opção)\s*([1-4])\b", normalized)
    if option_match:
        return int(option_match.group(1))

    for value, keywords in _OPTION_HINTS:
        if any(keyword in normalized for keyword in keywords):
            return value

    return None


def show_main_menu(
    *,
    instance: WhatsappInstance,
    phone: str,
    resident: Resident,
    session: ChatSession,
) -> None:
    transition(session, ChatSession.State.AWAITING_MAIN_MENU, reason="greeting_menu")
    send_whatsapp_reply(instance, phone, build_main_menu_message(resident=resident))


def handle_main_menu_message(
    *,
    instance: WhatsappInstance,
    phone: str,
    resident: Resident,
    session: ChatSession,
    text: str,
) -> bool:
    """Processa escolha no menu principal. Retorna True se tratou."""
    if session.state != ChatSession.State.AWAITING_MAIN_MENU:
        return False

    choice = parse_main_menu_choice(text)
    if choice is None:
        send_whatsapp_reply(instance, phone, build_main_menu_reminder())
        return True

    if choice == 1:
        cart = get_or_create_open_cart(resident)
        session.active_cart = cart
        session.save(update_fields=["active_cart", "updated_at"])
        transition(session, ChatSession.State.PRODUCT_SEARCH, reason="main_menu_purchase")
        send_whatsapp_reply(instance, phone, MAIN_MENU_PURCHASE_PROMPT)
        return True

    if choice == 2:
        transition(session, ChatSession.State.IDLE, reason="main_menu_maintenance")
        send_whatsapp_reply(instance, phone, build_maintenance_prompt())
        return True

    if choice == 3:
        transition(session, ChatSession.State.IDLE, reason="main_menu_stock")
        send_whatsapp_reply(instance, phone, build_stock_prompt())
        return True

    reset_to_idle(session, reason="main_menu_farewell")
    send_whatsapp_reply(
        instance,
        phone,
        build_main_menu_farewell(resident=resident),
    )
    return True

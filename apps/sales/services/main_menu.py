"""Menu principal de suporte após saudação (GREETING)."""

from __future__ import annotations

import logging
import re
import unicodedata

from apps.integrations.models import WhatsappInstance
from apps.residents.models import ChatSession, Resident
from apps.residents.services.whatsapp_reply import send_whatsapp_reply
from apps.sales.services.chat_fsm import transition
from apps.sales.services.intent_gatekeeper import is_opening_greeting
from apps.sales.services.resident_ai_context import resident_display_name
from apps.sales.services.whatsapp_interactive import (
    MAIN_MENU_ROW_IDS,
    MAIN_MENU_ROWS,
    MENU_BILLING,
    MENU_FRIDGE,
    MENU_OTHER,
    MENU_PAYMENT,
    MENU_PRODUCT,
    MENU_STORE,
    MENU_UNCATALOGUED,
    SUPPORT_DETAILS_PROMPT,
    UNREGISTERED_PRODUCT_SEARCH_PROMPT,
    build_main_menu_text_fallback,
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
}

_OPTION_HINTS: tuple[tuple[str, tuple[str, ...]], ...] = (
    (MENU_PAYMENT, ("maquininha", "indisp", "queda sistema", "pix nao funciona")),
    (MENU_UNCATALOGUED, ("sem cadastro", "sem preco", "nao cadastrado")),
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
    """Texto completo do menu de suporte."""
    return build_main_menu_text_fallback(greeting=build_main_menu_greeting(resident=resident))


def build_main_menu_reminder() -> str:
    lines = ["Não entendi. Escolha uma opção:"]
    for idx, (_row_id, title, _desc) in enumerate(MAIN_MENU_ROWS, start=1):
        lines.append(f"{idx} — {title}")
    return "\n".join(lines)


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

    max_opt = len(MAIN_MENU_ROWS)
    digit_head = re.match(rf"^([1-{max_opt}])", raw)
    if digit_head:
        rest = raw[digit_head.end() :]
        if not rest or re.fullmatch(r"[\ufe0f\u20e3\s]*", rest):
            return MAIN_MENU_ROWS[int(digit_head.group(1)) - 1][0]

    normalized = _normalize_choice_text(raw)
    if re.fullmatch(rf"[1-{max_opt}]", normalized):
        idx = int(normalized)
        return MAIN_MENU_ROWS[idx - 1][0]

    digit_match = re.search(rf"\b([1-{max_opt}])\b", normalized)
    if digit_match:
        idx = int(digit_match.group(1))
        return MAIN_MENU_ROWS[idx - 1][0]

    if normalized in _MENU_NUMBER_WORDS:
        idx = _MENU_NUMBER_WORDS[normalized]
        if 1 <= idx <= max_opt:
            return MAIN_MENU_ROWS[idx - 1][0]

    option_match = re.match(rf"^(?:opcao|opção)\s*([1-{max_opt}])\b", normalized)
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
    intro: str | None = None,
    reason: str = "greeting_menu",
) -> None:
    # Estado antes do envio — evita race se o morador responder muito rápido.
    transition(session, ChatSession.State.AWAITING_MAIN_MENU, reason=reason)
    menu_text = build_main_menu_message(resident=resident)
    body = menu_text
    intro_clean = (intro or "").strip()
    if intro_clean:
        body = f"{intro_clean}\n\n{menu_text}"
    # Listas nativas (/send/list) retornam 405 no WhatsApp via Evolution GO;
    # menu em texto numerado (igual ao catálogo de produtos).
    send_whatsapp_reply(instance, phone, body, session=session)


def _start_support_details_collection(
    *,
    instance: WhatsappInstance,
    phone: str,
    session: ChatSession,
    choice: str,
    reason: str,
) -> None:
    session.temporary_name = choice
    session.save(update_fields=["temporary_name", "updated_at"])
    transition(session, ChatSession.State.AWAITING_SUPPORT_DETAILS, reason=reason)
    send_whatsapp_reply(instance, phone, SUPPORT_DETAILS_PROMPT, session=session)


def _start_uncatalogued_product_search(
    *,
    instance: WhatsappInstance,
    phone: str,
    session: ChatSession,
) -> None:
    session.temporary_name = ""
    session.save(update_fields=["temporary_name", "updated_at"])
    transition(
        session,
        ChatSession.State.SEARCHING_UNREGISTERED_PRODUCT,
        reason="main_menu_uncatalogued",
    )
    send_whatsapp_reply(
        instance,
        phone,
        UNREGISTERED_PRODUCT_SEARCH_PROMPT,
        session=session,
    )


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

    if choice not in MAIN_MENU_ROW_IDS:
        logger.warning("Menu choice sem handler: %s", choice)
        send_whatsapp_reply(instance, phone, build_main_menu_reminder(), session=session)
        return True

    if choice == MENU_UNCATALOGUED:
        _start_uncatalogued_product_search(
            instance=instance,
            phone=phone,
            session=session,
        )
        return True

    reason_by_choice = {
        MENU_PAYMENT: "main_menu_payment",
        MENU_BILLING: "main_menu_billing",
        MENU_FRIDGE: "main_menu_fridge",
        MENU_STORE: "main_menu_store",
        MENU_PRODUCT: "main_menu_product_issue",
        MENU_OTHER: "main_menu_other",
    }
    _start_support_details_collection(
        instance=instance,
        phone=phone,
        session=session,
        choice=choice,
        reason=reason_by_choice.get(choice, "main_menu_support"),
    )
    return True

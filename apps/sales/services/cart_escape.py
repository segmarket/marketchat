"""Comandos globais de fuga e mapeamento de texto → ações do carrinho."""

from __future__ import annotations

import logging
import re
import unicodedata

from apps.integrations.models import WhatsappInstance
from apps.residents.models import Resident
from apps.residents.services.whatsapp_reply import send_whatsapp_reply
from apps.residents.models import ChatSession
from apps.sales.models import Cart, CartItem
from apps.sales.services.cart_session import unlock_resident_chat_session
from apps.sales.services.chat_fsm import reset_to_idle
from apps.sales.services.whatsapp_interactive import (
    CART_ADD_MORE,
    CART_CHECKOUT,
    parse_numeric_loop_choice,
)

logger = logging.getLogger(__name__)

GLOBAL_ESCAPE_EXACT = frozenset(
    {
        "cancela",
        "cancelar",
        "resetar",
        "sair",
        "nada",
        "esquece",
        "pare",
        "cancelar compra",
        "cancelar atendimento",
        "reiniciar",
    },
)

GLOBAL_ESCAPE_CONTAINS = (
    "cancelar compra",
    "cancelar atendimento",
    "cancele essa compra",
    "cancele essa compra ou esse atendimento",
    "cancelar essa compra",
    "cancelar esse atendimento",
    "nao quero nada",
    "nao quero",
    "deixa quieto",
    "deixa pra la",
    "esquece isso",
)

GLOBAL_ESCAPE_ACK_MESSAGE = (
    "Tudo bem! Atendimento encerrado. Se precisar, é só chamar! 👋"
)

FINALIZE_TEXT_KEYWORDS = ("finalizar", "pagar", "concluir", "fechar")
ADD_MORE_TEXT_KEYWORDS = ("adicionar", "mais", "continuar", "comprar mais")

RESTART_MESSAGE = (
    "Atendimento reiniciado e carrinho limpo! 🔄 O que você deseja buscar agora?"
)

LOOP_DECISION_FALLBACK = (
    "Por favor, responda:\n"
    "1 — Adicionar mais itens\n"
    "2 — Finalizar e pagar\n"
    "(Para limpar o carrinho e recomeçar, digite Cancelar)"
)

CANCELLABLE_CART_STATUSES = (
    Cart.Status.OPEN,
    Cart.Status.AWAITING_PHOTO,
    Cart.Status.AWAITING_PAYMENT,
)

CHECKOUT_PHOTO_MESSAGE = (
    "Perfeito! Envie uma foto dos seus produtos na gôndola para gerarmos seu Pix de pagamento."
)


PRODUCT_SEARCH_MIN_WORDS_FOR_CONVERSATIONAL_ESCAPE = 5

PRODUCT_SEARCH_INCIDENT_ROOTS = (
    "quebrad",
    "queimad",
    "problem",
    "defeit",
    "ruim",
    "não",
    "nao",
    "sujo",
    "vazand",
    "desligad",
    "parou",
    "caiu",
    "fechad",
    "travad",
    "cancel",
    "deixa",
    "esquec",
    "err",
    "frio",
    "quent",
)

PRODUCT_SEARCH_CONVERSATIONAL_TERMS = (
    "esta",
    "estao",
    "está",
    "estão",
    "tem",
    "foi",
    "aqui",
    "ali",
    "muito",
    "preciso",
    "quero",
    "ser",
    "tinha",
    "era",
    "ainda",
    "agora",
)


def _normalize_incident_text(text: str) -> str:
    lowered = (text or "").strip().lower()
    decomposed = unicodedata.normalize("NFD", lowered)
    return "".join(char for char in decomposed if unicodedata.category(char) != "Mn")


def _incident_tokens(normalized: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", normalized)


def _token_matches_incident_root(token: str, root: str) -> bool:
    if len(root) >= 4:
        return root in token
    return token == root or (token.startswith(root) and len(token) - len(root) <= 2)


def _has_incident_root(normalized: str) -> bool:
    tokens = _incident_tokens(normalized)
    if not tokens:
        return False
    blob = " ".join(tokens)
    for root in PRODUCT_SEARCH_INCIDENT_ROOTS:
        if len(root) >= 4 and root in blob:
            return True
    return any(
        _token_matches_incident_root(token, root)
        for token in tokens
        for root in PRODUCT_SEARCH_INCIDENT_ROOTS
        if len(root) < 4
    )


def _has_conversational_escape_signal(normalized: str, word_count: int) -> bool:
    if word_count < PRODUCT_SEARCH_MIN_WORDS_FOR_CONVERSATIONAL_ESCAPE:
        return False
    return any(term in normalized for term in PRODUCT_SEARCH_CONVERSATIONAL_TERMS)


def should_escape_product_search_for_intent(text: str) -> bool:
    """
    Detecta relatos de problema/manutenção antes da busca no catálogo (PRODUCT_SEARCH).
    """
    stripped = (text or "").strip()
    if not stripped:
        return False

    normalized = _normalize_incident_text(stripped)
    word_count = len(stripped.split())

    if _has_incident_root(normalized):
        return True

    return _has_conversational_escape_signal(normalized, word_count)


def is_global_escape_message(text: str) -> bool:
    """True se o morador pediu reinício/cancelamento global."""
    normalized = _normalize_incident_text(text)
    if not normalized:
        return False
    if normalized in GLOBAL_ESCAPE_EXACT:
        return True
    for phrase in GLOBAL_ESCAPE_CONTAINS:
        if phrase in normalized:
            return True
    if normalized in {"cancelar", "resetar", "sair", "reiniciar"}:
        return True
    if any(w in normalized for w in ("cancelar", "cancela", "cancele", "resetar", "reiniciar")):
        if any(w in normalized for w in ("compra", "atendimento", "carrinho")):
            return True
    return False


def cancel_open_carts_for_resident(resident: Resident) -> int:
    updated = Cart.objects.filter(
        tenant_id=resident.tenant_id,
        resident=resident,
        status__in=CANCELLABLE_CART_STATUSES,
    ).update(status=Cart.Status.CANCELLED)
    if updated:
        logger.info(
            "Carrinhos cancelados por escape global: resident=%s count=%s",
            resident.phone_number,
            updated,
        )
    return updated


def handle_global_escape(
    *,
    instance: WhatsappInstance,
    phone: str,
    resident: Resident,
    text: str,
) -> bool:
    """
    Botão de pânico: cancela carrinhos abertos, libera sessão e responde.
    Retorna True se a mensagem foi um comando de fuga.
    """
    if not is_global_escape_message(text):
        return False

    cancel_open_carts_for_resident(resident)
    session = (
        ChatSession.objects.filter(
            tenant_id=resident.tenant_id,
            phone_number=resident.phone_number,
        )
        .first()
    )
    if session:
        reset_to_idle(
            session,
            clear_cart_link=True,
            clear_discussed=True,
            reason="global_escape",
        )
    else:
        unlock_resident_chat_session(resident=resident, clear_cart_link=True)
    send_whatsapp_reply(instance, phone, GLOBAL_ESCAPE_ACK_MESSAGE)
    logger.info(
        "Escape global: tenant=%s phone=%s texto=%r",
        instance.tenant_id,
        phone,
        text[:80],
    )
    return True


def resolve_loop_choice_from_text(text: str) -> str | None:
    """Mapeia texto livre para CART_CHECKOUT ou CART_ADD_MORE."""
    normalized = (text or "").lower().strip()
    if not normalized:
        return None

    numeric = parse_numeric_loop_choice(text)
    if numeric:
        return numeric

    if any(keyword in normalized for keyword in FINALIZE_TEXT_KEYWORDS):
        return CART_CHECKOUT
    if any(keyword in normalized for keyword in ADD_MORE_TEXT_KEYWORDS):
        return CART_ADD_MORE
    return None


def cart_has_chargeable_items(cart: Cart | None) -> bool:
    if cart is None:
        return False
    return CartItem.objects.filter(cart=cart, quantity__gt=0).exists()


def try_checkout_from_text(
    *,
    instance: WhatsappInstance,
    phone: str,
    resident: Resident,
    session: ChatSession,
    text: str,
) -> bool:
    """
    Intercepta 'Finalizar' / 'Pagar' quando há carrinho ativo em IDLE.
    Evita que a OpenAI trate como despedida (CART_REVIEW usa _handle_loop_decision).
    """
    if session.state != ChatSession.State.IDLE:
        return False

    choice = resolve_loop_choice_from_text(text)
    if choice != CART_CHECKOUT:
        return False

    cart = session.active_cart
    if not cart_has_chargeable_items(cart):
        return False

    from apps.sales.services.chat_fsm import transition

    cart.recalculate_total()
    if cart.total_value <= 0:
        send_whatsapp_reply(
            instance,
            phone,
            "Seu carrinho está vazio. Adicione itens antes de finalizar.",
        )
        return True

    cart.status = Cart.Status.AWAITING_PHOTO
    cart.save(update_fields=["status", "updated_at"])
    transition(session, ChatSession.State.AWAITING_PHOTO, reason="checkout_intercept")
    send_whatsapp_reply(instance, phone, CHECKOUT_PHOTO_MESSAGE)
    logger.info(
        "Checkout interceptado: tenant=%s phone=%s cart=%s",
        instance.tenant_id,
        phone,
        cart.pk,
    )
    return True

"""Handlers de sugestão e conclusão do condomínio no onboarding."""

from __future__ import annotations

import logging
import re
import unicodedata

from apps.core.pii import mask_phone
from apps.integrations.models import WhatsappInstance
from apps.markets.models import Market
from apps.residents.models import ChatSession, Resident
from apps.residents.services.whatsapp_reply import send_whatsapp_reply

logger = logging.getLogger(__name__)

SUGGESTED_CONDOS_KEY = "suggested_condos"

RETRY_CONDO_NAME_MESSAGE = (
    "Sem problemas! Digite novamente o nome do seu condomínio para localizarmos sua unidade:"
)

CANCEL_KEYWORDS = frozenset(
    {
        "cancelar",
        "cancela",
        "voltar",
        "sair",
        "nao",
        "não",
        "n",
    }
)


def _normalize_cancel_text(text: str) -> str:
    lowered = (text or "").strip().lower()
    decomposed = unicodedata.normalize("NFD", lowered)
    return "".join(c for c in decomposed if unicodedata.category(c) != "Mn")


def build_condo_suggestions_message(suggestions: list[tuple[Market, float]]) -> str:
    lines = [
        "Hum... não achei exatamente esse condomínio, mas tenho essas opções "
        "parecidas cadastradas:",
        "",
    ]
    for idx, (market, _score) in enumerate(suggestions, start=1):
        lines.append(f"{idx} - {market.name}")
    lines.extend(
        [
            "",
            "Responda com o número da opção correta ou digite 'Cancelar' "
            "para tentar digitar o nome novamente.",
        ]
    )
    return "\n".join(lines)


def build_condo_list_all_message(suggestions: list[tuple[Market, float]]) -> str:
    lines = [
        "Não encontrei um condomínio com esse nome. Mas não se preocupe, "
        "veja a lista de mercados disponíveis:",
        "",
    ]
    for idx, (market, _score) in enumerate(suggestions, start=1):
        lines.append(f"{idx} - {market.name}")
    lines.extend(
        [
            "",
            "Responda com o número da opção correta.",
        ]
    )
    return "\n".join(lines)


def present_condo_suggestions(
    *,
    instance: WhatsappInstance,
    phone: str,
    session: ChatSession,
    suggestions: list[tuple[Market, float]],
    list_all: bool = False,
) -> None:
    """Persiste top sugestões e entra em AWAITING_CONDO_SUGGESTION."""
    payload = [
        {"id": market.id, "name": market.name}
        for market, _score in suggestions
    ]
    session.context_data = {SUGGESTED_CONDOS_KEY: payload}
    session.state = ChatSession.State.AWAITING_CONDO_SUGGESTION
    session.save(update_fields=["context_data", "state", "updated_at"])
    body = (
        build_condo_list_all_message(suggestions)
        if list_all
        else build_condo_suggestions_message(suggestions)
    )
    send_whatsapp_reply(
        instance,
        phone,
        body,
        session=session,
    )


def complete_condo_onboarding(
    *,
    instance: WhatsappInstance,
    phone: str,
    session: ChatSession,
    tenant_id: int,
    market: Market,
) -> None:
    """Cria/atualiza Resident, limpa sessão e abre o menu principal."""
    name = (session.temporary_name or "").strip()
    resident, _created = Resident.objects.update_or_create(
        tenant_id=tenant_id,
        phone_number=phone,
        defaults={
            "name": name,
            "market": market,
        },
    )
    session.temporary_name = ""
    session.context_data = {}
    session.active_cart = None
    session.pending_product = None
    session.save(
        update_fields=[
            "temporary_name",
            "context_data",
            "active_cart",
            "pending_product",
            "updated_at",
        ],
    )

    from apps.sales.services.main_menu import show_main_menu

    show_main_menu(
        instance=instance,
        phone=phone,
        resident=resident,
        session=session,
        intro=(
            f"Perfeito, identificamos o mercado no {market.name}!\n"
            "Seu cadastro foi concluído com sucesso."
        ),
        reason="onboarding_complete",
    )
    logger.info(
        "Morador cadastrado: tenant=%s phone=%s market=%s",
        tenant_id,
        mask_phone(phone),
        market.id,
    )


def _return_to_condo_name(
    *,
    instance: WhatsappInstance,
    phone: str,
    session: ChatSession,
) -> None:
    session.context_data = {}
    session.state = ChatSession.State.AWAITING_CONDO
    session.save(update_fields=["context_data", "state", "updated_at"])
    send_whatsapp_reply(
        instance,
        phone,
        RETRY_CONDO_NAME_MESSAGE,
        session=session,
    )


def handle_condo_suggestion_choice(
    *,
    instance: WhatsappInstance,
    phone: str,
    session: ChatSession,
    tenant_id: int,
    message: str,
) -> None:
    """Processa número / cancelar / inválido em AWAITING_CONDO_SUGGESTION."""
    raw = (message or "").strip()
    normalized = _normalize_cancel_text(raw)

    if normalized in CANCEL_KEYWORDS:
        _return_to_condo_name(instance=instance, phone=phone, session=session)
        return

    suggestions = list((session.context_data or {}).get(SUGGESTED_CONDOS_KEY) or [])
    digit_match = re.fullmatch(r"(\d{1,2})\ufe0f?\u20e3?", raw) or re.fullmatch(
        r"(\d{1,2})",
        normalized,
    )
    if not digit_match or not suggestions:
        _return_to_condo_name(instance=instance, phone=phone, session=session)
        return

    idx = int(digit_match.group(1))
    if idx < 1 or idx > len(suggestions):
        _return_to_condo_name(instance=instance, phone=phone, session=session)
        return

    chosen = suggestions[idx - 1]
    market_id = chosen.get("id")
    market = (
        Market.all_objects.filter(
            pk=market_id,
            tenant_id=tenant_id,
            status=Market.Status.ACTIVE,
        ).first()
        if market_id
        else None
    )
    if market is None:
        _return_to_condo_name(instance=instance, phone=phone, session=session)
        return

    complete_condo_onboarding(
        instance=instance,
        phone=phone,
        session=session,
        tenant_id=tenant_id,
        market=market,
    )

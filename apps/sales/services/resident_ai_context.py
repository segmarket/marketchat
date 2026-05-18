"""Contexto do morador para prompts da OpenAI."""

from __future__ import annotations

from apps.residents.models import Resident


def resident_display_name(resident: Resident) -> str:
    return (resident.name or "").strip() or "Morador"


def resident_market_name(resident: Resident) -> str:
    if resident.market_id:
        market = resident.market
        if market is not None:
            cleaned = (market.name or "").strip()
            if cleaned:
                return cleaned
    return "seu condomínio"


def build_resident_dynamic_context(resident: Resident) -> str:
    """Bloco dinâmico (final do system prompt) — nome e condomínio do morador atual."""
    name = resident_display_name(resident)
    market = resident_market_name(resident)
    return (
        f"Você está conversando com o morador chamado {name}, do condomínio {market}. "
        f"Sempre que o usuário iniciar uma conversa, cumprimente-o pelo nome de forma "
        f"calorosa e natural (ex: 'Olá, {name}! Como posso te ajudar hoje aqui no "
        f"mercado do {market}?'). Nunca seja genérico se você já sabe o nome dele."
    )


def build_resident_personalization_instructions(resident: Resident) -> str:
    """Compat: alias do bloco dinâmico."""
    return build_resident_dynamic_context(resident)


def build_complaint_dynamic_context(resident: Resident) -> str:
    """Contexto dinâmico quando a intenção classificada é reclamação."""
    base = build_resident_dynamic_context(resident)
    return (
        f"{base}\n\n"
        "Tipo de atendimento atual: RECLAMAÇÃO. "
        "Trate a mensagem do morador como uma insatisfação com produto, serviço "
        "ou experiência no mercado — não como pedido de compra nem falta de estoque."
    )


def build_payment_error_recovery_message(resident: Resident) -> str:
    name = resident_display_name(resident)
    return (
        f"Putz, lamento muito pelo problema com a maquininha física, {name}! 😕\n\n"
        "Mas não fique sem seus produtos por causa disso: você pode fazer sua compra "
        "e o pagamento via Pix por aqui mesmo no WhatsApp! É super rápido.\n\n"
        "Me diga: qual produto você deseja levar agora?"
    )

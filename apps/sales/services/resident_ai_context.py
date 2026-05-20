"""Contexto do morador para prompts da OpenAI."""

from __future__ import annotations

from apps.residents.models import Resident


def resident_first_name_from_string(raw: str | None) -> str:
    """Extrai o primeiro nome para saudações e prompts (ex.: 'João das Couves' -> 'João')."""
    cleaned = (raw or "").strip()
    if not cleaned:
        return "Morador"
    return cleaned.split()[0].capitalize()


def resident_display_name(resident: Resident) -> str:
    return resident_first_name_from_string(resident.name)


def resident_market_name(resident: Resident) -> str:
    if resident.market_id:
        market = resident.market
        if market is not None:
            cleaned = (market.name or "").strip()
            if cleaned:
                return cleaned
    return "seu condomínio"


def build_resident_dynamic_context(resident: Resident) -> str:
    """Bloco dinâmico (final do system prompt) — primeiro nome e condomínio do morador atual."""
    name = resident_display_name(resident)
    market = resident_market_name(resident)
    return (
        f"Você está conversando com o morador {name}, do condomínio {market}. "
        f"Use sempre apenas o primeiro nome dele ({name}) — nunca o nome completo. "
        f"Gírias e tom casual ('E ae', 'beleza', 'fala mano') são normais — responda com "
        f"simpatia e emojis quando fizer sentido. Em cumprimentos e dúvidas sobre compras "
        f"ou Pix, seja caloroso (ex: 'Fala, {name}! Beleza? Como posso te ajudar no mercado "
        f"do {market}?'). Modo seco e sem emojis apenas para abuso explícito, conforme a "
        f"diretriz anti-abuso do system prompt."
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

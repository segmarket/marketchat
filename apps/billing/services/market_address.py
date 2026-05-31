from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any


@dataclass
class MarketAddressParts:
    cep: str = ""
    street: str = ""
    number: str = ""
    complement: str = ""
    neighborhood: str = ""
    city: str = ""
    state: str = ""


def digits_only(value: str) -> str:
    return "".join(c for c in value if c.isdigit())


def parse_market_address(stored: str) -> MarketAddressParts:
    if not (stored or "").strip():
        return MarketAddressParts()

    try:
        data = json.loads(stored)
        if isinstance(data, dict) and isinstance(data.get("street"), str):
            cep_raw = str(data.get("cep") or "")
            cep_digits = digits_only(cep_raw)
            cep_display = cep_raw
            if len(cep_digits) == 8:
                cep_display = f"{cep_digits[:5]}-{cep_digits[5:]}"
            return MarketAddressParts(
                cep=cep_display,
                street=data.get("street") or "",
                number=str(data.get("number") or ""),
                complement=str(data.get("complement") or ""),
                neighborhood=str(data.get("neighborhood") or ""),
                city=str(data.get("city") or ""),
                state=str(data.get("state") or "").upper(),
            )
    except (json.JSONDecodeError, TypeError):
        pass

    return MarketAddressParts(street=stored.strip())


def market_address_is_valid(parts: MarketAddressParts) -> bool:
    return bool(
        len(digits_only(parts.cep)) == 8
        and parts.street.strip()
        and parts.number.strip()
        and parts.neighborhood.strip()
    )


def market_address_is_valid_for_subaccount(parts: MarketAddressParts) -> bool:
    """Endereço completo exigido pelo Asaas na criação da subconta (CEP resolve cidade)."""
    state = (parts.state or "").strip().upper()
    return bool(
        market_address_is_valid(parts)
        and parts.city.strip()
        and len(state) == 2
    )


def market_address_validation_message(parts: MarketAddressParts) -> str | None:
    if not parts.street.strip() and not parts.cep:
        return (
            "Cadastre ao menos um mercado com endereço completo em Meus Mercados "
            "antes de configurar o Pix."
        )
    if len(digits_only(parts.cep)) != 8:
        return "O mercado precisa ter um CEP válido (8 dígitos)."
    if not parts.street.strip():
        return "O mercado precisa ter a rua preenchida."
    if not parts.number.strip():
        return "O mercado precisa ter o número do endereço preenchido."
    if not parts.neighborhood.strip():
        return "O mercado precisa ter o bairro preenchido."
    return None


def market_address_validation_message_for_subaccount(parts: MarketAddressParts) -> str | None:
    msg = market_address_validation_message(parts)
    if msg:
        return msg
    if not parts.city.strip():
        return "O mercado precisa ter a cidade preenchida."
    state = (parts.state or "").strip().upper()
    if len(state) != 2:
        return "O mercado precisa ter o estado (UF) com 2 letras (ex.: SP)."
    return None

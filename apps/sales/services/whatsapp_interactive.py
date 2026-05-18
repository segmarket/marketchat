from __future__ import annotations

import logging
from decimal import Decimal

from apps.integrations.models import WhatsappInstance
from apps.products.models import Product
from apps.residents.services.whatsapp_reply import send_whatsapp_reply

logger = logging.getLogger(__name__)

PROD_ID_PREFIX = "prod:"
CART_ADD_MORE = "cart:add_more"
CART_CHECKOUT = "cart:checkout"


def _format_brl(value: Decimal) -> str:
    return f"R$ {value:.2f}".replace(".", ",")


def build_numbered_product_catalog(products: list[Product]) -> str:
    """Catálogo em texto puro (compatível com qualquer versão do WhatsApp)."""
    lines = ["Encontrei estes produtos:\n"]
    for idx, product in enumerate(products[:10], start=1):
        price_label = _format_brl(product.price)
        lines.append(f"{idx}. {product.name} — {price_label}")
    lines.append("\nResponda com o *número* do produto desejado (ex.: 1).")
    return "\n".join(lines)


def send_product_list(
    instance: WhatsappInstance,
    phone: str,
    products: list[Product],
) -> None:
    """Envia catálogo numerado em texto (sem carrossel/lista/botões nativos)."""
    if not products:
        return
    send_whatsapp_reply(instance, phone, build_numbered_product_catalog(products))


def send_cart_decision_buttons(
    instance: WhatsappInstance,
    phone: str,
    *,
    product_name: str,
    quantity: int,
    subtotal: Decimal,
) -> None:
    """Opções do carrinho em texto puro."""
    description = (
        f"{quantity}x {product_name}\n"
        f"Subtotal: {_format_brl(subtotal)}\n\n"
        "Deseja adicionar mais itens ou finalizar?"
    )
    send_whatsapp_reply(
        instance,
        phone,
        f"{description}\n\n"
        "Responda:\n"
        "*1* — Adicionar mais itens\n"
        "*2* — Finalizar e pagar\n\n"
        "Ou digite *Finalizar* / *Adicionar mais*.",
    )


def parse_numeric_product_choice(text: str, products: list[Product]) -> str | None:
    """Fallback: número 1-N → row id prod:sku."""
    stripped = (text or "").strip()
    if not stripped.isdigit():
        return None
    idx = int(stripped)
    if idx < 1 or idx > len(products):
        return None
    return f"{PROD_ID_PREFIX}{products[idx - 1].sku}"


def parse_numeric_loop_choice(text: str) -> str | None:
    stripped = (text or "").strip()
    if stripped == "1":
        return CART_ADD_MORE
    if stripped == "2":
        return CART_CHECKOUT
    return None

from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any

from apps.integrations.models import WhatsappInstance
from apps.integrations.services.evolution_client import EvolutionClient
from apps.products.models import Product
from apps.residents.services.whatsapp_reply import send_whatsapp_reply

logger = logging.getLogger(__name__)

PROD_ID_PREFIX = "prod:"
CART_ADD_MORE = "cart:add_more"
CART_CHECKOUT = "cart:checkout"

MENU_PURCHASE = "menu:purchase"
MENU_SUGGEST = "menu:suggest"
MENU_STOCK = "menu:stock"
MENU_UNCATALOGUED = "menu:uncatalogued"
MENU_PAYMENT = "menu:payment"
MENU_BILLING = "menu:billing"
MENU_FRIDGE = "menu:fridge"
MENU_STORE = "menu:store"
MENU_PRODUCT = "menu:product"
MENU_OTHER = "menu:other"

# Ordem = índice 1–10 do fallback numérico.
MAIN_MENU_ROWS: tuple[tuple[str, str, str], ...] = (
    (MENU_PURCHASE, "Fazer uma compra", "Buscar itens e pagar com Pix"),
    (MENU_SUGGEST, "Sugestão de produto", "Indicar produto que gostaria de ver"),
    (MENU_STOCK, "Falta de produto", "Avisar que algo acabou na gôndola"),
    (MENU_UNCATALOGUED, "Produto sem cadastro", "Item sem preço ou não encontrado"),
    (MENU_PAYMENT, "Indisp. de pagamento", "Maquininha ou Pix fora do ar"),
    (MENU_BILLING, "Problema cobrança", "Valor ou cobrança incorreta"),
    (MENU_FRIDGE, "Problema geladeira", "Geladeira ou freezer com defeito"),
    (MENU_STORE, "Problema loja", "Infraestrutura ou ambiente da loja"),
    (MENU_PRODUCT, "Problema com produto", "Qualidade, validade ou defeito"),
    (MENU_OTHER, "Outros assuntos", "Qualquer outro pedido de ajuda"),
)

MAIN_MENU_ROW_IDS = frozenset(row_id for row_id, _, _ in MAIN_MENU_ROWS)


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
    send_whatsapp_reply(
        instance,
        phone,
        (
            f"{quantity}x {product_name}\n"
            f"Subtotal: {_format_brl(subtotal)}\n\n"
            "Deseja adicionar mais itens ou finalizar?\n"
            "1 — Adicionar mais itens\n"
            "2 — Finalizar e pagar\n"
            "(Para limpar o carrinho e recomeçar, digite Cancelar)"
        ),
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


def build_main_menu_sections() -> list[dict[str, Any]]:
    rows = [
        {
            "rowId": row_id,
            "title": title[:24],
            "description": (description or "")[:72],
        }
        for row_id, title, description in MAIN_MENU_ROWS
    ]
    return [{"title": "Como podemos ajudar?", "rows": rows}]


def build_main_menu_text_fallback(*, greeting: str) -> str:
    lines = [greeting.strip(), ""]
    for idx, (_row_id, title, _desc) in enumerate(MAIN_MENU_ROWS, start=1):
        lines.append(f"{idx} — {title}")
    lines.append("")
    lines.append("Responda com o número da opção (1 a 10).")
    return "\n".join(lines)


def send_main_menu_list(
    instance: WhatsappInstance,
    phone: str,
    *,
    title: str,
    description: str,
) -> bool:
    """
    Envia lista interativa do menu. Retorna True se Evolution aceitou.
    Em falha o caller deve enviar o fallback em texto.
    """
    digits = "".join(c for c in phone if c.isdigit())
    if not digits:
        return False
    try:
        EvolutionClient().send_list(
            instance_api_key=instance.api_key,
            number=digits,
            title=title[:60] or "Menu",
            description=description[:1024] or "Escolha uma opção",
            button_text="Ver opções",
            sections=build_main_menu_sections(),
        )
        return True
    except Exception:
        logger.exception(
            "Falha ao enviar lista do menu: tenant=%s phone=%s",
            instance.tenant_id,
            digits,
        )
        return False

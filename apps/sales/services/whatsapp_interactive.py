from __future__ import annotations

from decimal import Decimal

from apps.integrations.models import WhatsappInstance
from apps.products.models import Product
from apps.residents.services.whatsapp_reply import send_whatsapp_reply

PROD_ID_PREFIX = "prod:"
CART_ADD_MORE = "cart:add_more"
CART_CHECKOUT = "cart:checkout"

# Mantidos para tipificação / legado; o menu principal só usa as 7 opções abaixo.
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

# Ordem = índice 1–7 do menu de suporte.
MAIN_MENU_ROWS: tuple[tuple[str, str, str], ...] = (
    (MENU_PAYMENT, "Indisp. de pagamento ou queda sistema", ""),
    (MENU_UNCATALOGUED, "Produto sem cadastro", ""),
    (MENU_BILLING, "Problema cobrança", ""),
    (MENU_FRIDGE, "Problema geladeira", ""),
    (MENU_STORE, "Problema loja", ""),
    (MENU_PRODUCT, "Problema com produto", ""),
    (MENU_OTHER, "Outros assuntos", ""),
)

MAIN_MENU_ROW_IDS = frozenset(row_id for row_id, _, _ in MAIN_MENU_ROWS)

SUPPORT_DETAILS_PROMPT = (
    "Entendido. Por favor, digite mais detalhes sobre o ocorrido "
    "para que nossa equipe possa te ajudar."
)

SUPPORT_HANDOVER_ACK = (
    "Obrigado pelas informações! Um atendente da nossa equipe "
    "vai te ajudar em breve."
)

SUPPORT_WAITING_QUEUE_MESSAGE = (
    "Sua solicitação foi registrada e nossa equipe já foi notificada! "
    "Um atendente assumirá essa conversa em instantes."
)

UNREGISTERED_PRODUCT_SEARCH_PROMPT = (
    "Qual produto deu como 'não cadastrado' na maquininha? "
    "Digite o nome ou marca para eu procurar no nosso sistema e tentar gerar o pagamento por aqui mesmo."
)

UNREGISTERED_PRODUCT_FOUND_INTRO = (
    "Boa notícia! Encontrei o produto aqui no sistema:"
)

UNREGISTERED_PRODUCT_FOUND_CTA = (
    "Deseja adicionar ao carrinho e pagar por aqui?"
)

UNREGISTERED_PRODUCT_NOT_FOUND_MESSAGE = (
    "Realmente esse produto não está aparecendo no meu sistema. "
    "Já notifiquei a equipe para realizar o cadastro e ajustar a maquininha! "
    "Um atendente assumirá essa conversa em instantes para te ajudar."
)


def build_uncatalogued_product_found_message(products: list[Product]) -> str:
    """Uma mensagem com intro, catálogo numerado e CTA (sem send_product_list duplicado)."""
    lines = [UNREGISTERED_PRODUCT_FOUND_INTRO, ""]
    for idx, product in enumerate(products[:10], start=1):
        price_label = _format_brl(product.price)
        lines.append(f"{idx}. {product.name} — {price_label}")
    lines.append("")
    lines.append(UNREGISTERED_PRODUCT_FOUND_CTA)
    lines.append("")
    lines.append("Responda com o *número* do produto desejado (ex.: 1).")
    return "\n".join(lines)


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


def build_main_menu_text_fallback(*, greeting: str) -> str:
    lines = [greeting.strip(), ""]
    for idx, (_row_id, title, _desc) in enumerate(MAIN_MENU_ROWS, start=1):
        lines.append(f"{idx} — {title}")
    lines.append("")
    lines.append(
        'Responda com o número da opção (1 a 7 ou Digite "sair" para reiniciar o menu).'
    )
    return "\n".join(lines)

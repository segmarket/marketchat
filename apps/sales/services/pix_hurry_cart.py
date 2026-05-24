"""Montagem rápida de carrinho a partir de mensagem com itens + Pix."""

from __future__ import annotations

import logging
import re

from apps.residents.models import ChatSession, Resident
from apps.sales.models import Cart, CartItem
from apps.sales.services.cart_repository import get_or_create_open_cart
from apps.sales.services.product_search import search_active_products

logger = logging.getLogger(__name__)

# Ex.: "3 cocas", "1 doritos", "peguei 2 coca cola lata"
_HURRY_ITEM_RE = re.compile(
    r"(?:^|[\s,;]|(?:e|and)\s+)(\d+)\s+"
    r"([a-záéíóúãõçA-ZÁÉÍÓÚÃÕÇ][\wáéíóúãõçÁÉÍÓÚÃÕÇ\s]{0,40}?)"
    r"(?=\s*(?:,|;|\.|$|e\s+\d|\s+e\s+|manda|pix|pra\s))",
    re.IGNORECASE,
)


def parse_hurry_line_items(message: str) -> list[tuple[int, str]]:
    """Extrai pares (quantidade, termo de busca) de frases informais de compra."""
    text = (message or "").strip()
    if not text:
        return []
    items: list[tuple[int, str]] = []
    seen: set[tuple[int, str]] = set()
    for match in _HURRY_ITEM_RE.finditer(text):
        qty = int(match.group(1))
        term = " ".join(match.group(2).split()).strip(" ,.;")
        if qty < 1 or len(term) < 2:
            continue
        key = (qty, term.lower())
        if key in seen:
            continue
        seen.add(key)
        items.append((qty, term))
    return items


def _resolve_product(tenant_id: int, term: str):
    products = search_active_products(tenant_id, term, limit=1)
    if products:
        return products[0]
    stripped = term.strip()
    if stripped.endswith("s") and len(stripped) > 3:
        products = search_active_products(tenant_id, stripped[:-1], limit=1)
        if products:
            return products[0]
    return None


def apply_pix_hurry_from_message(
    session: ChatSession,
    resident: Resident,
    user_message: str,
) -> bool:
    """
    Preenche o carrinho com itens citados na mensagem e avança para AWAITING_PHOTO.
    Retorna True se ao menos um produto do catálogo foi vinculado.
    """
    line_items = parse_hurry_line_items(user_message)
    if not line_items:
        return False

    cart = session.active_cart or get_or_create_open_cart(resident)
    session.active_cart = cart
    applied = 0

    for qty, term in line_items:
        product = _resolve_product(session.tenant_id, term)
        if not product:
            logger.info(
                "Pix pressa: produto não encontrado tenant=%s term=%r",
                session.tenant_id,
                term,
            )
            continue
        CartItem.objects.update_or_create(
            cart=cart,
            product=product,
            defaults={
                "quantity": qty,
                "unit_price": product.price,
            },
        )
        applied += 1

    if applied == 0:
        return False

    cart.recalculate_total()
    if cart.total_value <= 0:
        return False

    from apps.sales.services.chat_fsm import transition

    cart.status = Cart.Status.AWAITING_PHOTO
    cart.save(update_fields=["status", "updated_at"])
    session.temporary_name = ""
    session.pending_product = None
    session.save(
        update_fields=[
            "active_cart",
            "temporary_name",
            "pending_product",
            "updated_at",
        ],
    )
    transition(session, ChatSession.State.AWAITING_PHOTO, reason="pix_hurry")
    return True

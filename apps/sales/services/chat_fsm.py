"""Máquina de estados finitos (FSM) do fluxo de compra via WhatsApp."""

from __future__ import annotations

import logging

from apps.products.models import Product
from apps.residents.models import ChatSession

logger = logging.getLogger(__name__)

COMMERCE_STATES = frozenset(
    {
        ChatSession.State.PRODUCT_SEARCH,
        ChatSession.State.QUANTITY_SELECTION,
        ChatSession.State.CART_REVIEW,
        ChatSession.State.AWAITING_PHOTO,
    },
)

TRANSACTIONAL_STATES = COMMERCE_STATES | frozenset({ChatSession.State.IDLE})


def is_idle(session: ChatSession) -> bool:
    return session.state == ChatSession.State.IDLE


def is_commerce_state(session: ChatSession) -> bool:
    return session.state in COMMERCE_STATES


def is_transactional_state(session: ChatSession) -> bool:
    return session.state in TRANSACTIONAL_STATES


def transition(
    session: ChatSession,
    new_state: str,
    *,
    reason: str = "",
    clear_discussed: bool = False,
    clear_pending: bool = False,
    save: bool = True,
) -> None:
    old_state = session.state
    if old_state == new_state and not clear_discussed and not clear_pending:
        return

    session.state = new_state
    update_fields = ["state", "updated_at"]
    if clear_discussed:
        session.last_discussed_product = None
        update_fields.append("last_discussed_product")
    if clear_pending:
        session.pending_product = None
        update_fields.append("pending_product")

    if save:
        session.save(update_fields=update_fields)

    logger.info(
        "[FSM] tenant=%s phone=%s: %s -> %s (%s)",
        session.tenant_id,
        session.phone_number,
        old_state,
        new_state,
        reason or "transition",
    )


def record_discussed_product(session: ChatSession, product: Product | None) -> None:
    if product is None:
        return
    if session.last_discussed_product_id == product.pk:
        return
    session.last_discussed_product = product
    session.save(update_fields=["last_discussed_product", "updated_at"])
    logger.info(
        "[FSM] tenant=%s phone=%s: last_discussed_product=%s (%s)",
        session.tenant_id,
        session.phone_number,
        product.pk,
        product.name,
    )


def reset_to_idle(
    session: ChatSession,
    *,
    clear_cart_link: bool = True,
    clear_discussed: bool = True,
    reason: str = "reset",
) -> None:
    old_state = session.state
    session.state = ChatSession.State.IDLE
    session.pending_product = None
    session.temporary_name = ""
    update_fields = ["state", "pending_product", "temporary_name", "updated_at"]
    if clear_cart_link:
        session.active_cart = None
        update_fields.append("active_cart")
    if clear_discussed:
        session.last_discussed_product = None
        update_fields.append("last_discussed_product")
    session.save(update_fields=update_fields)
    logger.info(
        "[FSM] tenant=%s phone=%s: %s -> IDLE (%s)",
        session.tenant_id,
        session.phone_number,
        old_state,
        reason,
    )

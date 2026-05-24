"""Expiração preguiçosa: reseta sessão e carrinho após ociosidade prolongada."""

from __future__ import annotations

import logging
from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from apps.residents.models import ChatSession, Resident
from apps.sales.models import Cart
from apps.sales.services.cart_escape import cancel_open_carts_for_resident

logger = logging.getLogger(__name__)

_ONBOARDING_STATES = frozenset(
    {
        ChatSession.State.AWAITING_NAME,
        ChatSession.State.AWAITING_CONDO,
    },
)


def _lazy_expiry_minutes() -> int:
    return int(getattr(settings, "CHAT_SESSION_LAZY_EXPIRY_MINUTES", 30))


def _session_last_activity(session: ChatSession):
    return session.last_activity_at or session.updated_at


def _cancel_session_cart(session: ChatSession) -> None:
    cart = session.active_cart
    if cart is None:
        return
    if cart.status in (
        Cart.Status.OPEN,
        Cart.Status.AWAITING_PHOTO,
        Cart.Status.AWAITING_PAYMENT,
    ):
        cart.status = Cart.Status.CANCELLED
        cart.save(update_fields=["status", "updated_at"])


def maybe_reset_stale_chat_session(
    session: ChatSession,
    *,
    resident: Resident | None = None,
) -> bool:
    """
    Se a última interação exceder o limite configurado, cancela carrinhos abertos
    e volta a sessão para IDLE com contexto limpo. Deve rodar antes de touch_activity.
    """
    if session.state in _ONBOARDING_STATES:
        return False

    last_at = _session_last_activity(session)
    if not last_at:
        return False

    limit = timedelta(minutes=_lazy_expiry_minutes())
    if timezone.now() - last_at <= limit:
        return False

    if resident is not None:
        cancel_open_carts_for_resident(resident)
    else:
        _cancel_session_cart(session)

    session.state = ChatSession.State.IDLE
    session.active_cart = None
    session.pending_product = None
    session.last_discussed_product = None
    session.temporary_name = ""
    session.inactivity_notified = False
    session.save(
        update_fields=[
            "state",
            "active_cart",
            "pending_product",
            "last_discussed_product",
            "temporary_name",
            "inactivity_notified",
            "updated_at",
        ],
    )

    logger.info(
        "[FSM Reset] Sessão phone=%s tenant=%s resetada por ociosidade (>%s min).",
        session.phone_number,
        session.tenant_id,
        _lazy_expiry_minutes(),
    )
    return True

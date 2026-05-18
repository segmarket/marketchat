"""Sessão de chat vinculada ao fluxo de compra."""

from __future__ import annotations

from apps.residents.models import ChatSession, Resident
from apps.sales.models import Cart


def unlock_resident_chat_session(
    *,
    resident: Resident,
    clear_cart_link: bool = True,
) -> None:
    """Libera o morador para novas interações (estado ACTIVE_BOT)."""
    updates = {
        "state": ChatSession.State.ACTIVE_BOT,
        "pending_product": None,
        "temporary_name": "",
    }
    if clear_cart_link:
        updates["active_cart"] = None

    from django.utils import timezone

    updates["last_activity_at"] = timezone.now()
    updates["inactivity_notified"] = False

    ChatSession.objects.filter(
        tenant_id=resident.tenant_id,
        phone_number=resident.phone_number,
    ).update(**updates)


def link_session_to_cart(session: ChatSession, cart: Cart) -> None:
    session.active_cart = cart
    session.save(update_fields=["active_cart", "updated_at"])

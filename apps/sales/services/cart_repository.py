from __future__ import annotations

from apps.residents.models import Resident
from apps.sales.models import Cart


def get_or_create_open_cart(resident: Resident) -> Cart:
    """Retorna carrinho ativo (OPEN ou em fluxo de foto) do morador."""
    active_statuses = (
        Cart.Status.OPEN,
        Cart.Status.AWAITING_PHOTO,
    )
    cart = (
        Cart.objects.filter(
            tenant_id=resident.tenant_id,
            resident_id=resident.id,
            status__in=active_statuses,
        )
        .order_by("-created_at")
        .first()
    )
    if cart:
        return cart
    return Cart.objects.create(
        tenant_id=resident.tenant_id,
        resident_id=resident.id,
        status=Cart.Status.OPEN,
    )

"""Strategy Pattern — dispatcher do menu de suporte (opções 1–7)."""

from __future__ import annotations

from collections.abc import Callable

from apps.integrations.models import WhatsappInstance
from apps.residents.models import ChatSession, Resident
from apps.sales.services.handlers import (
    catalog,
    generic,
    infrastructure,
    payment,
    product_quality,
)
from apps.sales.services.whatsapp_interactive import (
    MENU_BILLING,
    MENU_FRIDGE,
    MENU_OTHER,
    MENU_PAYMENT,
    MENU_PRODUCT,
    MENU_STORE,
    MENU_UNCATALOGUED,
)

SupportMenuHandler = Callable[..., bool]

SUPPORT_MENU_HANDLERS: dict[str, SupportMenuHandler] = {
    "1": payment.handle_payment_unavailable,
    MENU_PAYMENT: payment.handle_payment_unavailable,
    "2": catalog.handle_missing_product,
    MENU_UNCATALOGUED: catalog.handle_missing_product,
    "3": payment.handle_billing_issue,
    MENU_BILLING: payment.handle_billing_issue,
    "4": infrastructure.handle_infrastructure_issue,
    MENU_FRIDGE: infrastructure.handle_infrastructure_issue,
    "5": infrastructure.handle_infrastructure_issue,
    MENU_STORE: infrastructure.handle_infrastructure_issue,
    "6": product_quality.handle_quality_issue,
    MENU_PRODUCT: product_quality.handle_quality_issue,
    "7": generic.handle_generic_issue,
    MENU_OTHER: generic.handle_generic_issue,
}


def dispatch_support_menu_choice(
    *,
    choice: str,
    instance: WhatsappInstance,
    phone: str,
    resident: Resident,
    session: ChatSession,
    text: str = "",
) -> bool | None:
    """
    Resolve e executa o handler da opção.
    Retorna True/False do handler, ou None se não houver handler registrado.
    """
    handler = SUPPORT_MENU_HANDLERS.get(choice)
    if handler is None:
        return None
    return handler(
        instance=instance,
        phone=phone,
        resident=resident,
        session=session,
        text=text,
        choice_code=choice,
    )


__all__ = [
    "SUPPORT_MENU_HANDLERS",
    "dispatch_support_menu_choice",
]

"""Webhook Asaas: confirmação e expiração de Pix de carrinhos WhatsApp."""

from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any

from django.db import transaction

from apps.billing.services.asaas_client import AsaasAPIError, AsaasClient
from apps.billing.services.asaas_webhook_payload import parse_cart_id_from_external_reference
from apps.integrations.models import WhatsappInstance
from apps.residents.models import Resident
from apps.residents.services.whatsapp_reply import send_whatsapp_reply
from apps.sales.models import Cart
from apps.sales.services.cart_session import unlock_resident_chat_session
from apps.tenants.context import tenant_scope

logger = logging.getLogger(__name__)

PAYMENT_SUCCESS_EVENTS = frozenset(
    {
        "PAYMENT_RECEIVED",
        "PAYMENT_CONFIRMED",
        "PAYMENT_RECEIVED_IN_CASH",
    },
)
PAYMENT_EXPIRED_EVENTS = frozenset({"PAYMENT_OVERDUE"})
PAYMENT_CANCELLED_EVENTS = frozenset({"PAYMENT_DELETED"})

ASAAS_PAID_STATUSES = frozenset(
    {
        "RECEIVED",
        "CONFIRMED",
        "RECEIVED_IN_CASH",
    },
)


def _format_brl(value: Decimal) -> str:
    return f"R$ {value:.2f}".replace(".", ",")


def _payment_id_from_payload(payment: dict[str, Any]) -> str:
    return str(payment.get("id") or "").strip()


def find_cart_for_asaas_payment(payment: dict[str, Any]) -> Cart | None:
    """Localiza carrinho por asaas_billing_id ou externalReference."""
    payment_id = _payment_id_from_payload(payment)
    if payment_id:
        cart = (
            Cart.objects.filter(asaas_billing_id=payment_id)
            .select_related("resident", "resident__market", "tenant")
            .first()
        )
        if cart:
            return cart

    cart_id = parse_cart_id_from_external_reference(
        str(payment.get("externalReference") or ""),
    )
    if cart_id:
        return (
            Cart.objects.filter(pk=cart_id)
            .select_related("resident", "resident__market", "tenant")
            .first()
        )

    return None


def _whatsapp_instance_for_tenant(tenant_id: int) -> WhatsappInstance | None:
    return (
        WhatsappInstance.objects.filter(tenant_id=tenant_id, is_active=True)
        .order_by("-id")
        .first()
    )


def _build_payment_confirmed_message(cart: Cart, resident: Resident) -> str:
    name = (resident.name or "").strip() or "Morador"
    market = (resident.market.name if resident.market_id else "seu condomínio").strip()
    total = _format_brl(cart.total_value)
    return (
        "PAGAMENTO CONFIRMADO!\n\n"
        f"Obrigado, {name}! Seu pagamento de {total} foi recebido com sucesso. "
        f"Seus produtos estão liberados para retirada no mercado do {market}. "
        "Tenha um excelente dia!"
    )


def _build_payment_expired_message(cart: Cart) -> str:
    total = _format_brl(cart.total_value)
    return (
        "⚠️ PIX EXPIRADO: O código Pix para a sua compra de "
        f"{total} expirou porque o pagamento não foi identificado dentro do prazo.\n\n"
        "Se você ainda quiser levar os produtos, não tem problema! "
        "Basta digitar o que deseja comprar aqui no chat para iniciar um novo carrinho."
    )


@transaction.atomic
def handle_cart_payment_received(cart: Cart) -> bool:
    if cart.status == Cart.Status.COMPLETED:
        logger.info(
            "Carrinho já concluído: cart_id=%s payment=%s",
            cart.id,
            cart.asaas_billing_id,
        )
        return False

    cart.status = Cart.Status.COMPLETED
    cart.save(update_fields=["status", "updated_at"])

    resident = cart.resident
    unlock_resident_chat_session(resident=resident, clear_cart_link=True)

    instance = _whatsapp_instance_for_tenant(cart.tenant_id)
    if instance:
        send_whatsapp_reply(
            instance,
            resident.phone_number,
            _build_payment_confirmed_message(cart, resident),
        )
    else:
        logger.warning(
            "Pagamento confirmado sem WhatsApp ativo: tenant=%s cart=%s",
            cart.tenant_id,
            cart.id,
        )

    logger.info(
        "Pix confirmado: cart_id=%s resident=%s total=%s",
        cart.id,
        resident.phone_number,
        cart.total_value,
    )
    return True


@transaction.atomic
def handle_cart_payment_expired(cart: Cart, *, cancelled: bool = False) -> bool:
    terminal = {Cart.Status.COMPLETED, Cart.Status.CANCELLED, Cart.Status.EXPIRED}
    if cart.status in terminal:
        logger.info(
            "Carrinho já finalizado (%s): cart_id=%s",
            cart.status,
            cart.id,
        )
        return False

    cart.status = Cart.Status.CANCELLED if cancelled else Cart.Status.EXPIRED
    cart.save(update_fields=["status", "updated_at"])

    resident = cart.resident
    unlock_resident_chat_session(resident=resident, clear_cart_link=True)

    instance = _whatsapp_instance_for_tenant(cart.tenant_id)
    if instance:
        send_whatsapp_reply(
            instance,
            resident.phone_number,
            _build_payment_expired_message(cart),
        )

    logger.info(
        "Pix expirado/cancelado: cart_id=%s status=%s resident=%s",
        cart.id,
        cart.status,
        resident.phone_number,
    )
    return True


def process_cart_asaas_event(*, event: str, payment: dict[str, Any]) -> bool:
    """
    Processa evento Asaas se houver carrinho vinculado.
    Retorna True se o evento foi tratado (carrinho atualizado).
    """
    payment_id = _payment_id_from_payload(payment)
    if not payment_id and not payment.get("externalReference"):
        return False

    cart = find_cart_for_asaas_payment(payment)
    if cart is None:
        logger.info(
            "Webhook Asaas: nenhum carrinho para payment_id=%s externalReference=%s event=%s",
            payment_id,
            payment.get("externalReference"),
            event,
        )
        return False

    if payment_id and not cart.asaas_billing_id:
        cart.asaas_billing_id = payment_id
        cart.save(update_fields=["asaas_billing_id", "updated_at"])

    event_upper = (event or "").upper()
    logger.info(
        "Webhook Asaas (carrinho): event=%s payment_id=%s cart_id=%s tenant=%s status=%s",
        event_upper,
        payment_id,
        cart.id,
        cart.tenant_id,
        cart.status,
    )

    with tenant_scope(cart.tenant_id):
        if event_upper in PAYMENT_SUCCESS_EVENTS:
            return handle_cart_payment_received(cart)
        if event_upper in PAYMENT_EXPIRED_EVENTS:
            return handle_cart_payment_expired(cart, cancelled=False)
        if event_upper in PAYMENT_CANCELLED_EVENTS:
            return handle_cart_payment_expired(cart, cancelled=True)

    logger.info(
        "Webhook Asaas: evento %s ignorado para cart_id=%s",
        event_upper,
        cart.id,
    )
    return False


def sync_cart_payment_from_asaas(cart: Cart) -> bool:
    """
    Consulta GET /payments/{id} no Asaas (útil em sandbox/local sem webhook público).
    Retorna True se o carrinho foi marcado como pago.
    """
    payment_id = (cart.asaas_billing_id or "").strip()
    if not payment_id:
        logger.info("sync_cart_payment: cart %s sem asaas_billing_id", cart.id)
        return False

    client = AsaasClient()
    try:
        payment = client.get_payment(payment_id)
    except AsaasAPIError as exc:
        logger.warning(
            "sync_cart_payment: falha GET payment %s cart=%s: %s",
            payment_id,
            cart.id,
            exc.payload,
        )
        return False

    status = str(payment.get("status") or "").upper()
    logger.info(
        "sync_cart_payment: cart=%s payment=%s status=%s",
        cart.id,
        payment_id,
        status,
    )

    if status not in ASAAS_PAID_STATUSES:
        return False

    with tenant_scope(cart.tenant_id):
        return handle_cart_payment_received(cart)

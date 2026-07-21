"""Cobrança PIX avulsa gerada pelo atendente no chat."""

from __future__ import annotations

import logging
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any

from apps.billing.services.asaas_client import AsaasAPIError, AsaasClient
from apps.billing.services.asaas_errors import format_asaas_error
from apps.billing.services.asaas_pix_charge import (
    PixChargeError,
    extract_pix_copy_paste,
    fetch_pix_copy_paste,
    get_or_create_resident_customer,
)
from apps.billing.services.asaas_webhook_payload import cart_external_reference
from apps.residents.models import ChatSession, Resident
from apps.sales.models import Cart, CartItem

logger = logging.getLogger(__name__)


class ChatPixChargeError(Exception):
    """Erro de negócio na cobrança PIX do chat."""


def _to_decimal(value: Any) -> Decimal:
    try:
        return Decimal(str(value)).quantize(Decimal("0.01"))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ChatPixChargeError("Valor inválido.") from exc


def _resolve_resident(tenant_id: int, session: ChatSession) -> Resident:
    resident = (
        Resident.objects.filter(
            tenant_id=tenant_id,
            phone_number=session.phone_number,
            is_active=True,
            is_anonymized=False,
        )
        .select_related("market")
        .first()
    )
    if resident is None:
        raise ChatPixChargeError(
            "Morador não encontrado para esta conversa. "
            "É necessário cadastro ativo para gerar cobrança.",
        )
    return resident


def _normalize_items(
    *,
    items: list[dict[str, Any]] | None,
    amount: Decimal | None,
) -> list[tuple[str, int, Decimal]]:
    """Retorna lista (name, quantity, unit_price). amount avulso tem prioridade."""
    if amount is not None:
        if amount <= 0:
            raise ChatPixChargeError("Informe um valor maior que zero.")
        return [("Cobrança avulsa", 1, amount)]

    if not items:
        raise ChatPixChargeError("Informe itens ou um valor avulso.")

    normalized: list[tuple[str, int, Decimal]] = []
    for raw in items:
        name = str(raw.get("name") or "").strip()
        if not name:
            raise ChatPixChargeError("Cada item precisa de um nome.")
        try:
            qty = int(raw.get("quantity") or 0)
        except (TypeError, ValueError) as exc:
            raise ChatPixChargeError("Quantidade inválida.") from exc
        if qty <= 0:
            raise ChatPixChargeError("Quantidade deve ser maior que zero.")
        unit = _to_decimal(raw.get("unit_price"))
        if unit <= 0:
            raise ChatPixChargeError("Valor unitário deve ser maior que zero.")
        normalized.append((name[:255], qty, unit))

    if not normalized:
        raise ChatPixChargeError("Informe pelo menos um item.")
    return normalized


def _build_description(
    *,
    lines: list[tuple[str, int, Decimal]],
    description: str,
    cart_id: int,
) -> str:
    custom = (description or "").strip()
    if custom:
        return custom[:500]
    if len(lines) == 1 and lines[0][0] == "Cobrança avulsa":
        return f"Cobrança avulsa chat — pedido #{cart_id}"
    names = ", ".join(f"{n} x{q}" for n, q, _ in lines[:5])
    if len(lines) > 5:
        names += "…"
    return f"Cobrança chat — pedido #{cart_id}: {names}"[:500]


def _invoice_url(payment: dict[str, Any]) -> str:
    for key in ("invoiceUrl", "bankSlipUrl", "transactionReceiptUrl"):
        val = payment.get(key)
        if isinstance(val, str) and val.strip():
            return val.strip()
    return ""


def generate_chat_pix_charge(
    *,
    tenant_id: int,
    session_id: int,
    items: list[dict[str, Any]] | None = None,
    amount: Decimal | None = None,
    description: str = "",
) -> dict[str, Any]:
    """
    Cria Cart + itens + cobrança PIX Asaas.
    Retorna pix_copia_e_cola, invoice_url, amount, cart_id, description, items_summary.
    """
    session = ChatSession.objects.filter(tenant_id=tenant_id, pk=session_id).first()
    if session is None:
        raise ChatPixChargeError("Conversa não encontrada.")

    resident = _resolve_resident(tenant_id, session)
    lines = _normalize_items(items=items, amount=amount)

    cart = Cart.objects.create(
        tenant_id=tenant_id,
        resident=resident,
        status=Cart.Status.OPEN,
    )
    for name, qty, unit in lines:
        CartItem.objects.create(
            cart=cart,
            product=None,
            item_name=name,
            quantity=qty,
            unit_price=unit,
        )
    total = cart.recalculate_total()
    if total <= 0:
        cart.status = Cart.Status.CANCELLED
        cart.save(update_fields=["status", "updated_at"])
        raise ChatPixChargeError("Valor total inválido.")

    charge_description = _build_description(
        lines=lines,
        description=description,
        cart_id=cart.id,
    )

    client = AsaasClient()
    try:
        customer_id = get_or_create_resident_customer(resident, client)
    except PixChargeError as exc:
        cart.status = Cart.Status.CANCELLED
        cart.save(update_fields=["status", "updated_at"])
        raise ChatPixChargeError(str(exc)) from exc

    body: dict[str, Any] = {
        "customer": customer_id,
        "billingType": "PIX",
        "value": float(total),
        "dueDate": date.today().isoformat(),
        "description": charge_description,
        "externalReference": cart_external_reference(cart.id),
    }

    try:
        payment = client.create_payment(body)
    except AsaasAPIError as exc:
        logger.warning("Erro Asaas create_payment (chat): %s", exc.payload)
        cart.status = Cart.Status.CANCELLED
        cart.save(update_fields=["status", "updated_at"])
        raise ChatPixChargeError(format_asaas_error(exc)) from exc

    payment_id = str(payment.get("id") or "").strip()
    pix_code = extract_pix_copy_paste(payment)
    if not pix_code and payment_id:
        try:
            pix_code = fetch_pix_copy_paste(client, payment_id)
        except PixChargeError as exc:
            cart.status = Cart.Status.CANCELLED
            cart.save(update_fields=["status", "updated_at"])
            raise ChatPixChargeError(str(exc)) from exc

    invoice = _invoice_url(payment)
    if not pix_code:
        cart.status = Cart.Status.CANCELLED
        cart.save(update_fields=["status", "updated_at"])
        if invoice:
            raise ChatPixChargeError(
                "Cobrança criada no Asaas, mas o código Pix não foi gerado. "
                f"Link: {invoice}",
            )
        raise ChatPixChargeError(
            "Não foi possível obter o código Pix. Verifique a chave Pix no Asaas.",
        )

    cart.asaas_billing_id = payment_id
    cart.status = Cart.Status.AWAITING_PAYMENT
    cart.save(update_fields=["asaas_billing_id", "status", "updated_at"])

    items_summary = [
        {"name": n, "quantity": q, "unit_price": str(u), "subtotal": str(u * q)}
        for n, q, u in lines
    ]

    return {
        "pix_copia_e_cola": pix_code,
        "invoice_url": invoice,
        "amount": str(total),
        "cart_id": cart.id,
        "description": charge_description,
        "items_summary": items_summary,
    }

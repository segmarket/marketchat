from __future__ import annotations

import logging
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.financial.choices import PixKeyType
from apps.financial.models import LedgerTransaction, Wallet, WithdrawalRequest
from apps.financial.services.asaas_transfers import (
    AsaasTransferError,
    map_transfer_status_to_withdrawal,
    normalize_pix_key_for_asaas,
    process_asaas_pix_transfer,
)
from apps.sales.models import Cart

logger = logging.getLogger(__name__)

STATEMENT_PAGE_SIZE = 20


class WalletError(Exception):
    pass


class InsufficientBalanceError(WalletError):
    pass


@dataclass
class StatementPage:
    wallet: Wallet
    balance_available: Decimal
    balance_blocked: Decimal
    balance_processing: Decimal
    fee_percent: Decimal
    results: list[LedgerTransaction]
    page: int
    total_count: int
    next_page: int | None
    previous_page: int | None


def _quantize_money(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def platform_fee_percent() -> Decimal:
    return Decimal(str(getattr(settings, "FINANCIAL_PLATFORM_FEE_PERCENT", 2)))


def calculate_net_amount(gross_amount: Decimal) -> tuple[Decimal, Decimal]:
    gross = _quantize_money(gross_amount)
    fee_pct = platform_fee_percent()
    fee = _quantize_money(gross * fee_pct / Decimal("100"))
    net = _quantize_money(gross - fee)
    return net, fee


def _format_brl(value: Decimal) -> str:
    return f"R$ {value:.2f}".replace(".", ",")


def build_sale_description(cart: Cart) -> str:
    items = list(
        cart.items.select_related("product").filter(quantity__gt=0).order_by("id")[:4],
    )
    if not items:
        return f"Venda — carrinho #{cart.id}"

    names = [item.product.name for item in items[:3]]
    extra = len(items) - len(names)
    label = ", ".join(names)
    if extra > 0:
        label = f"{label} e mais {extra} item(ns)"
    return f"Venda — {label}"


def _lock_wallet(tenant_id: int) -> Wallet:
    wallet, _created = Wallet.objects.select_for_update().get_or_create(
        tenant_id=tenant_id,
    )
    return wallet


def _processing_balance(wallet: Wallet) -> Decimal:
    from django.db.models import Sum

    result = WithdrawalRequest.objects.filter(
        wallet=wallet,
        status=WithdrawalRequest.Status.PROCESSING,
    ).aggregate(total=Sum("amount"))["total"]
    return _quantize_money(result or Decimal("0"))


@transaction.atomic
def credit_sale_payment(
    cart: Cart,
    payment_id: str,
    gross_amount: Decimal | None = None,
) -> LedgerTransaction | None:
    """
    Credita o valor líquido (após taxa da plataforma) na carteira do tenant.
    Idempotente por external_id (payment_id do Asaas).
    """
    payment_id = (payment_id or cart.asaas_billing_id or "").strip()
    if not payment_id:
        logger.warning("credit_sale_payment: cart=%s sem payment_id", cart.id)
        return None

    if LedgerTransaction.objects.filter(external_id=payment_id).exists():
        logger.info("credit_sale_payment: já creditado payment_id=%s", payment_id)
        return None

    gross = _quantize_money(gross_amount if gross_amount is not None else cart.total_value)
    if gross <= Decimal("0"):
        return None

    net, fee = calculate_net_amount(gross)
    wallet = _lock_wallet(cart.tenant_id)

    description = build_sale_description(cart)
    if fee > Decimal("0"):
        description = (
            f"{description} (bruto {_format_brl(gross)}, taxa {platform_fee_percent():.0f}%: "
            f"{_format_brl(fee)})"
        )

    wallet.balance_available = _quantize_money(wallet.balance_available + net)
    wallet.save(update_fields=["balance_available", "updated_at"])

    ledger = LedgerTransaction.objects.create(
        wallet=wallet,
        amount=net,
        entry_type=LedgerTransaction.EntryType.INFLOW,
        description=description,
        external_id=payment_id,
        cart=cart,
    )
    logger.info(
        "Carteira creditada: tenant=%s cart=%s gross=%s net=%s payment=%s",
        cart.tenant_id,
        cart.id,
        gross,
        net,
        payment_id,
    )
    return ledger


@transaction.atomic
def update_wallet_pix_settings(
    *,
    tenant_id: int,
    pix_key: str,
    pix_key_type: str,
) -> Wallet:
    if pix_key_type not in PixKeyType.values:
        raise WalletError("Tipo de chave Pix inválido.")

    normalized = normalize_pix_key_for_asaas(pix_key_type, pix_key)
    wallet = _lock_wallet(tenant_id)
    wallet.default_pix_key = normalized
    wallet.default_pix_key_type = pix_key_type
    wallet.save(update_fields=["default_pix_key", "default_pix_key_type", "updated_at"])
    return wallet


@transaction.atomic
def request_withdrawal(
    *,
    tenant_id: int,
    amount: Decimal,
) -> WithdrawalRequest:
    amount = _quantize_money(amount)
    if amount <= Decimal("0"):
        raise WalletError("Informe um valor de saque maior que zero.")

    wallet = _lock_wallet(tenant_id)
    if not wallet.has_default_pix_key:
        raise WalletError("Configure sua chave Pix antes de solicitar um saque.")

    if amount > wallet.balance_available:
        raise InsufficientBalanceError("Saldo insuficiente para este saque.")

    pix_key = wallet.default_pix_key
    pix_key_type = wallet.default_pix_key_type

    transfer_data = process_asaas_pix_transfer(
        value=amount,
        pix_key=pix_key,
        pix_key_type=pix_key_type,
        description="Saque MarketChat",
    )

    transfer_id = str(transfer_data.get("id") or "").strip()
    withdrawal_status = map_transfer_status_to_withdrawal(str(transfer_data.get("status") or ""))

    wallet.balance_available = _quantize_money(wallet.balance_available - amount)
    wallet.save(update_fields=["balance_available", "updated_at"])

    ledger = LedgerTransaction.objects.create(
        wallet=wallet,
        amount=amount,
        entry_type=LedgerTransaction.EntryType.OUTFLOW,
        description="Saque Pix",
        external_id=transfer_id,
    )

    withdrawal = WithdrawalRequest.objects.create(
        wallet=wallet,
        amount=amount,
        pix_key=pix_key,
        pix_key_type=pix_key_type,
        status=withdrawal_status,
        asaas_transfer_id=transfer_id,
        ledger_transaction=ledger,
        processed_at=timezone.now() if withdrawal_status == WithdrawalRequest.Status.PAID else None,
    )
    logger.info(
        "Saque Pix automático: tenant=%s amount=%s transfer=%s status=%s",
        tenant_id,
        amount,
        transfer_id,
        withdrawal_status,
    )
    return withdrawal


@transaction.atomic
def mark_withdrawal_paid(withdrawal: WithdrawalRequest) -> bool:
    if withdrawal.status == WithdrawalRequest.Status.PAID:
        return False
    if withdrawal.status == WithdrawalRequest.Status.REJECTED:
        return False

    if withdrawal.status == WithdrawalRequest.Status.PENDING:
        wallet = Wallet.objects.select_for_update().get(pk=withdrawal.wallet_id)
        amount = _quantize_money(withdrawal.amount)
        wallet.balance_blocked = _quantize_money(max(Decimal("0"), wallet.balance_blocked - amount))
        wallet.save(update_fields=["balance_blocked", "updated_at"])

    withdrawal.status = WithdrawalRequest.Status.PAID
    withdrawal.processed_at = timezone.now()
    withdrawal.save(update_fields=["status", "processed_at"])
    return True


@transaction.atomic
def mark_withdrawal_rejected(withdrawal: WithdrawalRequest) -> bool:
    if withdrawal.status == WithdrawalRequest.Status.PAID:
        return False
    if withdrawal.status == WithdrawalRequest.Status.REJECTED:
        return False

    wallet = Wallet.objects.select_for_update().get(pk=withdrawal.wallet_id)
    amount = _quantize_money(withdrawal.amount)
    update_fields = ["updated_at"]

    if withdrawal.status == WithdrawalRequest.Status.PENDING:
        wallet.balance_blocked = _quantize_money(max(Decimal("0"), wallet.balance_blocked - amount))
        wallet.balance_available = _quantize_money(wallet.balance_available + amount)
        update_fields.extend(["balance_blocked", "balance_available"])
    elif withdrawal.status == WithdrawalRequest.Status.PROCESSING:
        wallet.balance_available = _quantize_money(wallet.balance_available + amount)
        update_fields.append("balance_available")

    wallet.save(update_fields=update_fields)

    withdrawal.status = WithdrawalRequest.Status.REJECTED
    withdrawal.processed_at = timezone.now()
    withdrawal.save(update_fields=["status", "processed_at"])
    return True


def get_statement(tenant_id: int, *, page: int = 1) -> StatementPage:
    wallet, _created = Wallet.get_or_create_for_tenant(tenant_id)
    page = max(1, page)
    qs = LedgerTransaction.objects.filter(wallet=wallet).order_by("-created_at", "-id")
    total_count = qs.count()
    offset = (page - 1) * STATEMENT_PAGE_SIZE
    results = list(qs[offset : offset + STATEMENT_PAGE_SIZE])

    total_pages = max(1, (total_count + STATEMENT_PAGE_SIZE - 1) // STATEMENT_PAGE_SIZE)
    next_page = page + 1 if page < total_pages else None
    previous_page = page - 1 if page > 1 else None

    processing = _processing_balance(wallet)

    return StatementPage(
        wallet=wallet,
        balance_available=wallet.balance_available,
        balance_blocked=wallet.balance_blocked,
        balance_processing=processing,
        fee_percent=platform_fee_percent(),
        results=results,
        page=page,
        total_count=total_count,
        next_page=next_page,
        previous_page=previous_page,
    )


def withdrawal_success_message(status: str) -> str:
    if status == WithdrawalRequest.Status.PAID:
        return "Saque enviado! O Pix será creditado em instantes."
    return "Saque em processamento. Acompanhe no extrato."

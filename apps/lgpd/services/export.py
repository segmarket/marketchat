"""Exportação de dados pessoais (portabilidade LGPD)."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from django.contrib.auth import get_user_model

from apps.billing.models import Subscription
from apps.financial.models import LedgerTransaction, Wallet
from apps.markets.models import Market
from apps.residents.models import ChatMessage, ChatSession, Resident
from apps.sales.models import Cart, CartItem
from apps.tenants.models import Tenant

User = get_user_model()


def _decimal_str(value: Decimal | None) -> str:
    if value is None:
        return "0.00"
    return f"{value:.2f}"


def build_tenant_export_json(*, tenant: Tenant, user: User) -> dict[str, Any]:
    markets = list(
        Market.objects.filter(tenant=tenant).values(
            "id", "name", "address", "status", "created_at", "updated_at"
        )
    )
    for row in markets:
        row["created_at"] = row["created_at"].isoformat() if row["created_at"] else None
        row["updated_at"] = row["updated_at"].isoformat() if row["updated_at"] else None

    wallet_payload = None
    ledger_rows: list[dict[str, Any]] = []
    wallet = Wallet.objects.filter(tenant=tenant).first()
    if wallet:
        wallet_payload = {
            "balance_available": _decimal_str(wallet.balance_available),
            "balance_blocked": _decimal_str(wallet.balance_blocked),
            "default_pix_key_type": wallet.default_pix_key_type,
            "has_pix_key_configured": wallet.has_default_pix_key,
        }
        for tx in LedgerTransaction.objects.filter(wallet=wallet).order_by("-created_at")[:500]:
            ledger_rows.append(
                {
                    "id": tx.id,
                    "amount": _decimal_str(tx.amount),
                    "entry_type": tx.entry_type,
                    "description": tx.description,
                    "external_id": tx.external_id or None,
                    "cart_id": tx.cart_id,
                    "created_at": tx.created_at.isoformat(),
                }
            )

    subscription_payload = None
    try:
        sub = tenant.subscription
        subscription_payload = {
            "status": sub.status,
            "trial_ends_at": sub.trial_ends_at.isoformat(),
            "asaas_subscription_id": sub.asaas_subscription_id,
        }
    except Subscription.DoesNotExist:
        pass

    return {
        "export_type": "tenant",
        "exported_at": tenant.updated_at.isoformat(),
        "user": {
            "id": user.id,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "phone": user.phone,
            "is_tenant_admin": user.is_tenant_admin,
        },
        "tenant": {
            "id": tenant.id,
            "name": tenant.name,
            "slug": tenant.slug,
            "phone": tenant.phone,
            "cpf_cnpj": tenant.cpf_cnpj,
            "subscription_status": tenant.subscription_status,
            "trial_started_at": tenant.trial_started_at.isoformat(),
            "trial_ends_at": tenant.trial_ends_at.isoformat(),
            "terms_accepted_at": (
                tenant.terms_accepted_at.isoformat() if tenant.terms_accepted_at else None
            ),
            "created_at": tenant.created_at.isoformat(),
        },
        "markets": markets,
        "wallet": wallet_payload,
        "ledger_transactions": ledger_rows,
        "subscription": subscription_payload,
    }


def build_resident_export_json(*, resident: Resident) -> dict[str, Any]:
    sessions = ChatSession.objects.filter(
        tenant_id=resident.tenant_id,
        phone_number=resident.phone_number,
    )
    messages: list[dict[str, Any]] = []
    for session in sessions:
        for msg in ChatMessage.objects.filter(session=session).order_by("created_at"):
            messages.append(
                {
                    "session_id": session.id,
                    "role": msg.role,
                    "content": msg.content,
                    "created_at": msg.created_at.isoformat(),
                }
            )

    carts: list[dict[str, Any]] = []
    for cart in Cart.objects.filter(resident=resident).prefetch_related("items").order_by("-created_at"):
        items = [
            {
                "product_id": item.product_id,
                "product_name": item.product.name if item.product_id else "",
                "quantity": item.quantity,
                "unit_price": _decimal_str(item.unit_price),
            }
            for item in cart.items.select_related("product")
        ]
        carts.append(
            {
                "id": cart.id,
                "status": cart.status,
                "total_value": _decimal_str(cart.total_value),
                "has_security_photo": bool(cart.product_photo),
                "created_at": cart.created_at.isoformat(),
                "items": items,
            }
        )

    return {
        "export_type": "resident",
        "resident": {
            "id": resident.id,
            "name": resident.name,
            "phone_number": resident.phone_number,
            "market_id": resident.market_id,
            "market_name": resident.market.name if resident.market_id else None,
            "is_active": resident.is_active,
            "is_anonymized": resident.is_anonymized,
            "anonymized_at": (
                resident.anonymized_at.isoformat() if resident.anonymized_at else None
            ),
            "created_at": resident.created_at.isoformat(),
        },
        "chat_messages": messages,
        "orders": carts,
    }

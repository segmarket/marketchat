"""Suspensão automática por trial vencido ou inadimplência fora da carência."""

from __future__ import annotations

import logging
import urllib.error
from dataclasses import dataclass
from datetime import timedelta
from typing import Iterator, Literal

from django.conf import settings
from django.db.models import Q
from django.utils import timezone

from apps.accounts.models import User
from apps.billing.models import Subscription
from apps.core.emails import send_subscription_suspended_email_safe
from apps.integrations.models import WhatsappInstance
from apps.integrations.services.provisioning import logout_whatsapp_session
from apps.residents.models import ChatSession
from apps.sales.models import Cart
from apps.sales.services.cart_session import unlock_resident_chat_session
from apps.tenants.models import Tenant

logger = logging.getLogger(__name__)

SuspensionReason = Literal["trial_expired", "billing_overdue"]

_REASON_LABELS: dict[SuspensionReason, str] = {
    "trial_expired": "período de testes encerrado",
    "billing_overdue": "fatura em atraso",
}

_ACTIVE_CART_STATUSES = (
    Cart.Status.OPEN,
    Cart.Status.AWAITING_PHOTO,
    Cart.Status.AWAITING_PAYMENT,
)

_PURCHASE_SESSION_STATES = (
    ChatSession.State.AWAITING_MAIN_MENU,
    ChatSession.State.AWAITING_SUPPORT_DETAILS,
    ChatSession.State.SEARCHING_UNREGISTERED_PRODUCT,
    ChatSession.State.WAITING_FOR_HUMAN,
    ChatSession.State.PRODUCT_SEARCH,
    ChatSession.State.QUANTITY_SELECTION,
    ChatSession.State.CART_REVIEW,
    ChatSession.State.AWAITING_PHOTO,
)


@dataclass(frozen=True)
class PendingSuspension:
    tenant: Tenant
    reason: SuspensionReason


def _grace_days() -> int:
    return int(getattr(settings, "BILLING_GRACE_DAYS", 3))


def suspension_reason_for_tenant(tenant: Tenant, *, now=None) -> SuspensionReason | None:
    """Retorna o motivo de suspensão pendente ou None."""
    now = now or timezone.now()
    if tenant.subscription_status in (
        Tenant.SubscriptionStatus.SUSPENDED,
        Tenant.SubscriptionStatus.CANCELED,
    ):
        return None
    if (
        tenant.subscription_status == Tenant.SubscriptionStatus.TRIAL
        and tenant.trial_ends_at < now
    ):
        return "trial_expired"
    if tenant.subscription_status == Tenant.SubscriptionStatus.OVERDUE:
        if tenant.overdue_since is None:
            return None
        cutoff = now - timedelta(days=_grace_days())
        if tenant.overdue_since <= cutoff:
            return "billing_overdue"
    return None


def iter_tenants_pending_suspension(*, now=None) -> Iterator[PendingSuspension]:
    now = now or timezone.now()
    grace_cutoff = now - timedelta(days=_grace_days())

    qs = (
        Tenant.objects.exclude(
            subscription_status__in=(
                Tenant.SubscriptionStatus.SUSPENDED,
                Tenant.SubscriptionStatus.CANCELED,
            ),
        )
        .filter(
            Q(
                subscription_status=Tenant.SubscriptionStatus.TRIAL,
                trial_ends_at__lt=now,
            )
            | Q(
                subscription_status=Tenant.SubscriptionStatus.OVERDUE,
                overdue_since__isnull=False,
                overdue_since__lte=grace_cutoff,
            ),
        )
        .order_by("pk")
    )

    for tenant in qs.iterator():
        reason = suspension_reason_for_tenant(tenant, now=now)
        if reason:
            yield PendingSuspension(tenant=tenant, reason=reason)


def logout_tenant_whatsapp_sessions(tenant_id: int) -> None:
    """Logout Evolution de todas as instâncias ativas; propaga falha para não suspender no banco."""
    instances = list(
        WhatsappInstance.all_objects.filter(tenant_id=tenant_id, is_active=True),
    )
    if not instances:
        return
    for instance in instances:
        logout_whatsapp_session(instance)


def clear_tenant_operational_state(tenant_id: int) -> int:
    """Cancela carrinhos abertos e libera sessões de chat. Retorna carrinhos cancelados."""
    carts = list(
        Cart.objects.filter(
            tenant_id=tenant_id,
            status__in=_ACTIVE_CART_STATUSES,
        ).select_related("resident"),
    )
    cancelled = 0
    for cart in carts:
        cart.status = Cart.Status.CANCELLED
        cart.save(update_fields=["status", "updated_at"])
        unlock_resident_chat_session(resident=cart.resident, clear_cart_link=True)
        cancelled += 1

    ChatSession.objects.filter(tenant_id=tenant_id).filter(
        Q(active_cart__isnull=False) | Q(state__in=_PURCHASE_SESSION_STATES),
    ).update(
        state=ChatSession.State.IDLE,
        active_cart=None,
        pending_product=None,
        temporary_name="",
        last_discussed_product=None,
        inactivity_notified=False,
        last_activity_at=timezone.now(),
    )
    return cancelled


def _apply_tenant_suspended_state(tenant: Tenant, *, reason: SuspensionReason) -> None:
    tenant.subscription_status = Tenant.SubscriptionStatus.SUSPENDED
    tenant.block_billing_access()
    update_fields = ["subscription_status", "billing_blocked_at", "updated_at"]
    tenant.save(update_fields=update_fields)

    if reason == "trial_expired":
        try:
            sub = tenant.subscription
        except Subscription.DoesNotExist:
            return
        if sub.status != Subscription.Status.INACTIVE:
            sub.status = Subscription.Status.INACTIVE
            sub.save(update_fields=["status", "updated_at"])


def _notify_tenant_admin(tenant: Tenant, *, reason: SuspensionReason) -> None:
    admin = (
        User.objects.filter(tenant_id=tenant.pk, is_tenant_admin=True)
        .order_by("pk")
        .first()
    )
    if admin is None:
        logger.warning("Tenant %s suspenso sem admin para e-mail", tenant.pk)
        return
    send_subscription_suspended_email_safe(
        admin,
        tenant,
        reason=reason,
        reason_label=_REASON_LABELS[reason],
    )


def enforce_tenant_suspension(
    tenant: Tenant,
    *,
    reason: SuspensionReason,
    send_email: bool = True,
) -> bool:
    """
    Suspende tenant após logout Evolution bem-sucedido.
    Retorna False se logout falhar (tenant permanece no status atual).
    """
    if tenant.subscription_status in (
        Tenant.SubscriptionStatus.SUSPENDED,
        Tenant.SubscriptionStatus.CANCELED,
    ):
        return False

    try:
        logout_tenant_whatsapp_sessions(tenant.pk)
    except (urllib.error.HTTPError, urllib.error.URLError, OSError, TimeoutError, RuntimeError) as exc:
        logger.warning(
            "Suspensão adiada: logout Evolution falhou tenant_id=%s reason=%s err=%s",
            tenant.pk,
            reason,
            exc,
        )
        return False
    except Exception as exc:
        logger.warning(
            "Suspensão adiada: erro inesperado no logout tenant_id=%s reason=%s err=%s",
            tenant.pk,
            reason,
            exc,
            exc_info=True,
        )
        return False

    _apply_tenant_suspended_state(tenant, reason=reason)
    carts_cancelled = clear_tenant_operational_state(tenant.pk)
    if send_email:
        _notify_tenant_admin(tenant, reason=reason)

    logger.info(
        "Tenant suspenso tenant_id=%s slug=%s reason=%s carts_cancelled=%s",
        tenant.pk,
        tenant.slug,
        reason,
        carts_cancelled,
    )
    return True

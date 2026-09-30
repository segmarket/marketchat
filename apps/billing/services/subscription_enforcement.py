"""
Suspensão automática por trial vencido ou inadimplência fora da carência.

O bloqueio local (status, billing_blocked_at, carrinhos/sessões) é aplicado na hora;
o logout Evolution é uma etapa separada, registrada como pendente e reexecutada pelo
check_subscriptions até confirmar (ou até o tenant se regularizar).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Iterator, Literal

from django.db import transaction
from django.db.models import F, Q
from django.utils import timezone

from apps.accounts.models import User
from apps.billing.models import Subscription
from apps.core.emails import send_subscription_suspended_email_safe
from apps.integrations.models import WhatsappInstance
from apps.integrations.services.provisioning import logout_whatsapp_session
from apps.residents.models import ChatSession
from apps.sales.models import Cart
from apps.sales.services.cart_session import unlock_resident_chat_session
from apps.tenants.billing_rules import grace_expired, grace_expired_cutoff
from apps.tenants.models import Tenant

logger = logging.getLogger(__name__)

LogoutOutcome = Literal["done", "failed", "not_pending", "cancelled_regularized"]

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
        and tenant.trial_ends_at <= now
    ):
        return "trial_expired"
    if tenant.subscription_status == Tenant.SubscriptionStatus.OVERDUE:
        if grace_expired(tenant.overdue_since, now=now):
            return "billing_overdue"
    return None


def iter_tenants_pending_suspension(*, now=None) -> Iterator[PendingSuspension]:
    now = now or timezone.now()
    grace_cutoff = grace_expired_cutoff(now=now)

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
                trial_ends_at__lte=now,
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


def iter_canceled_tenants_pending_block(*, now=None) -> Iterator[Tenant]:
    """CANCELED com trial encerrado e ainda sem bloqueio (ex.: cancelou durante o trial)."""
    now = now or timezone.now()
    qs = Tenant.objects.filter(
        subscription_status=Tenant.SubscriptionStatus.CANCELED,
        billing_blocked_at__isnull=True,
        trial_ends_at__lte=now,
    ).order_by("pk")
    yield from qs.iterator()


def iter_tenants_pending_suspension_email() -> Iterator[Tenant]:
    """Suspensos sem aviso deste bloqueio (ex.: suspensos na request ou falha de SMTP)."""
    qs = (
        Tenant.objects.filter(
            subscription_status=Tenant.SubscriptionStatus.SUSPENDED,
            billing_blocked_at__isnull=False,
        )
        .filter(
            Q(billing_suspension_notified_at__isnull=True)
            | Q(billing_suspension_notified_at__lt=F("billing_blocked_at")),
        )
        .order_by("pk")
    )
    yield from qs.iterator()


def iter_tenants_pending_whatsapp_logout() -> Iterator[Tenant]:
    qs = Tenant.objects.filter(whatsapp_logout_pending_since__isnull=False).order_by(
        "whatsapp_logout_pending_since",
        "pk",
    )
    yield from qs.iterator()


def logout_tenant_whatsapp_sessions(tenant_id: int) -> None:
    """Logout Evolution de todas as instâncias ativas; propaga a primeira falha."""
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


def _tenant_is_blocked(tenant: Tenant) -> bool:
    return (
        tenant.subscription_status == Tenant.SubscriptionStatus.SUSPENDED
        or tenant.billing_blocked_at is not None
    )


def _open_whatsapp_logout_pendency(tenant: Tenant, now) -> list[str]:
    """Abre a pendência de logout; tentativas e erro de um bloqueio anterior já regularizado não contam."""
    if tenant.whatsapp_logout_pending_since is not None:
        return []
    tenant.whatsapp_logout_pending_since = now
    tenant.whatsapp_logout_attempts = 0
    tenant.whatsapp_logout_last_attempt_at = None
    tenant.whatsapp_logout_last_error = ""
    return [
        "whatsapp_logout_pending_since",
        "whatsapp_logout_attempts",
        "whatsapp_logout_last_attempt_at",
        "whatsapp_logout_last_error",
    ]


def _apply_tenant_suspended_state(tenant: Tenant, *, reason: SuspensionReason) -> None:
    now = timezone.now()
    tenant.subscription_status = Tenant.SubscriptionStatus.SUSPENDED
    tenant.billing_blocked_at = tenant.billing_blocked_at or now
    logout_fields = _open_whatsapp_logout_pendency(tenant, now)
    tenant.save(
        update_fields=[
            "subscription_status",
            "billing_blocked_at",
            *logout_fields,
            "updated_at",
        ],
    )

    if reason == "trial_expired":
        try:
            sub = tenant.subscription
        except Subscription.DoesNotExist:
            return
        if sub.status != Subscription.Status.INACTIVE:
            sub.status = Subscription.Status.INACTIVE
            sub.save(update_fields=["status", "updated_at"])


def _notify_tenant_admin(tenant: Tenant, *, reason: SuspensionReason) -> bool:
    admin = (
        User.objects.filter(tenant_id=tenant.pk, is_tenant_admin=True)
        .order_by("pk")
        .first()
    )
    if admin is None:
        logger.warning("Tenant %s suspenso sem admin para e-mail", tenant.pk)
        return False
    return send_subscription_suspended_email_safe(
        admin,
        tenant,
        reason=reason,
        reason_label=_REASON_LABELS[reason],
    )


def send_suspension_email(tenant: Tenant, *, reason: SuspensionReason | None = None) -> bool:
    """Avisa o admin do bloqueio atual; sem envio confirmado, o aviso segue pendente para o próximo ciclo."""
    if reason is None:
        reason = "billing_overdue" if tenant.overdue_since else "trial_expired"
    if not _notify_tenant_admin(tenant, reason=reason):
        return False
    now = timezone.now()
    Tenant.objects.filter(pk=tenant.pk).update(billing_suspension_notified_at=now)
    tenant.billing_suspension_notified_at = now
    return True


def attempt_pending_whatsapp_logout(tenant: Tenant) -> LogoutOutcome:
    """
    Uma tentativa de logout Evolution para um bloqueio já aplicado localmente.
    Se o tenant se regularizou nesse meio tempo, a pendência é descartada sem logout.
    """
    tenant.refresh_from_db()
    if tenant.whatsapp_logout_pending_since is None:
        return "not_pending"
    if not _tenant_is_blocked(tenant) and tenant.has_messaging_access():
        tenant.whatsapp_logout_pending_since = None
        tenant.save(update_fields=["whatsapp_logout_pending_since", "updated_at"])
        logger.info("Logout Evolution descartado (tenant regularizado) tenant_id=%s", tenant.pk)
        return "cancelled_regularized"

    now = timezone.now()
    tenant.whatsapp_logout_attempts += 1
    tenant.whatsapp_logout_last_attempt_at = now
    try:
        logout_tenant_whatsapp_sessions(tenant.pk)
    except Exception as exc:
        tenant.whatsapp_logout_last_error = f"{type(exc).__name__}: {exc}"[:500]
        tenant.save(
            update_fields=[
                "whatsapp_logout_attempts",
                "whatsapp_logout_last_attempt_at",
                "whatsapp_logout_last_error",
                "updated_at",
            ],
        )
        logger.warning(
            "Logout Evolution pendente tenant_id=%s tentativa=%s pendente_desde=%s err=%s",
            tenant.pk,
            tenant.whatsapp_logout_attempts,
            tenant.whatsapp_logout_pending_since.isoformat(),
            tenant.whatsapp_logout_last_error,
        )
        return "failed"

    tenant.whatsapp_logout_pending_since = None
    tenant.whatsapp_logout_last_error = ""
    tenant.save(
        update_fields=[
            "whatsapp_logout_pending_since",
            "whatsapp_logout_attempts",
            "whatsapp_logout_last_attempt_at",
            "whatsapp_logout_last_error",
            "updated_at",
        ],
    )
    logger.info(
        "Logout Evolution concluído tenant_id=%s tentativas=%s",
        tenant.pk,
        tenant.whatsapp_logout_attempts,
    )
    return "done"


def enforce_tenant_suspension(
    tenant: Tenant,
    *,
    reason: SuspensionReason,
    send_email: bool = True,
    attempt_logout: bool = True,
) -> bool:
    """
    Bloqueia o tenant localmente e registra o logout Evolution como pendente.
    Com attempt_logout=True faz a primeira tentativa na hora; falhas ficam para o retry.
    Retorna True se o bloqueio foi aplicado agora.
    """
    with transaction.atomic():
        locked = Tenant.objects.select_for_update().get(pk=tenant.pk)
        if suspension_reason_for_tenant(locked) != reason:
            return False
        _apply_tenant_suspended_state(locked, reason=reason)
        carts_cancelled = clear_tenant_operational_state(locked.pk)

    tenant.refresh_from_db()
    logger.info(
        "Tenant suspenso tenant_id=%s slug=%s reason=%s carts_cancelled=%s",
        tenant.pk,
        tenant.slug,
        reason,
        carts_cancelled,
    )
    if send_email:
        send_suspension_email(tenant, reason=reason)
    if attempt_logout:
        attempt_pending_whatsapp_logout(tenant)
        tenant.refresh_from_db()
    return True


def block_canceled_tenant(tenant: Tenant, *, attempt_logout: bool = True) -> bool:
    """CANCELED com trial encerrado: bloqueia painel e bot mantendo o status (reativável)."""
    with transaction.atomic():
        locked = Tenant.objects.select_for_update().get(pk=tenant.pk)
        if (
            locked.subscription_status != Tenant.SubscriptionStatus.CANCELED
            or locked.billing_blocked_at is not None
            or locked.trial_ends_at > timezone.now()
        ):
            return False
        now = timezone.now()
        locked.billing_blocked_at = now
        logout_fields = _open_whatsapp_logout_pendency(locked, now)
        locked.save(update_fields=["billing_blocked_at", *logout_fields, "updated_at"])
        clear_tenant_operational_state(locked.pk)

    logger.info("Tenant cancelado bloqueado após o trial tenant_id=%s", tenant.pk)
    if attempt_logout:
        attempt_pending_whatsapp_logout(tenant)
    tenant.refresh_from_db()
    return True

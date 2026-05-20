"""Encerramento educado de sessões WhatsApp inativas (fluxos não-Pix)."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import timedelta

from django.db.models import Q
from django.utils import timezone

from apps.integrations.models import WhatsappInstance
from apps.residents.models import ChatSession, Resident
from apps.residents.services.whatsapp_reply import send_whatsapp_reply
from apps.sales.models import Cart
from apps.sales.services.cart_escape import cancel_open_carts_for_resident
from apps.sales.services.resident_ai_context import (
    resident_display_name,
    resident_first_name_from_string,
)
from apps.tenants.context import tenant_scope

logger = logging.getLogger(__name__)

DEFAULT_MIN_IDLE_MINUTES = 5
DEFAULT_MAX_IDLE_MINUTES = 15

# Estados elegíveis: conversa geral ou decisão de carrinho (não fluxo Pix/foto).
INACTIVITY_ELIGIBLE_STATES = frozenset(
    {
        ChatSession.State.IDLE,
        ChatSession.State.CART_REVIEW,
    },
)

PURCHASE_FLOW_STATES = frozenset(
    {
        ChatSession.State.PRODUCT_SEARCH,
        ChatSession.State.QUANTITY_SELECTION,
        ChatSession.State.AWAITING_PHOTO,
    },
)


@dataclass
class InactivityFollowupResult:
    scanned: int = 0
    sent: int = 0
    skipped: int = 0
    errors: int = 0


def _greeting_period() -> str:
    hour = timezone.localtime().hour
    if 6 <= hour < 18:
        return "dia"
    return "noite"


def build_inactivity_closing_message(
    *,
    resident_name: str,
    market_name: str,
) -> str:
    """Mensagem de encerramento por inatividade (tom acolhedor, PT-BR)."""
    name = (resident_name or "").strip() or "tudo bem"
    market = (market_name or "").strip() or "seu condomínio"
    period = _greeting_period()
    return (
        f"Olá, {name}! Como não tivemos novas mensagens por aqui nos últimos minutos, "
        f"estou encerrando nosso atendimento para manter o canal livre.\n\n"
        f"O registro do seu chamado/feedback no mercado do {market} foi salvo com sucesso! "
        f"Se precisar de mais alguma coisa, basta me mandar um 'Oi' que estarei por aqui. "
        f"Tenha um excelente {period}! 👋"
    )


def resolve_resident_for_session(session: ChatSession) -> Resident | None:
    return (
        Resident.objects.filter(
            tenant_id=session.tenant_id,
            phone_number=session.phone_number,
        )
        .select_related("market")
        .first()
    )


def resolve_whatsapp_instance(tenant_id: int) -> WhatsappInstance | None:
    return (
        WhatsappInstance.objects.filter(
            tenant_id=tenant_id,
            is_active=True,
        )
        .order_by("-updated_at")
        .first()
    )


def session_excluded_from_inactivity(session: ChatSession) -> bool:
    """Ignora fluxo de compra/Pix e pagamento pendente."""
    if session.state in PURCHASE_FLOW_STATES:
        return True
    if session.state not in INACTIVITY_ELIGIBLE_STATES:
        return True
    cart = session.active_cart
    if cart is not None and cart.status == Cart.Status.AWAITING_PAYMENT:
        return True
    return False


def reset_chat_session_after_inactivity(session: ChatSession) -> None:
    """Volta ao modo limpo após encerramento por inatividade."""
    session.state = ChatSession.State.IDLE
    session.active_cart = None
    session.pending_product = None
    session.last_discussed_product = None
    session.temporary_name = ""
    session.inactivity_notified = False
    session.last_activity_at = timezone.now()
    session.save(
        update_fields=[
            "state",
            "active_cart",
            "pending_product",
            "last_discussed_product",
            "temporary_name",
            "inactivity_notified",
            "last_activity_at",
            "updated_at",
        ],
    )


def queryset_stale_sessions(
    *,
    min_idle_minutes: int = DEFAULT_MIN_IDLE_MINUTES,
    max_idle_minutes: int = DEFAULT_MAX_IDLE_MINUTES,
):
    now = timezone.now()
    oldest = now - timedelta(minutes=max_idle_minutes)
    newest = now - timedelta(minutes=min_idle_minutes)

    return (
        ChatSession.objects.filter(
            state__in=INACTIVITY_ELIGIBLE_STATES,
            inactivity_notified=False,
            last_activity_at__gte=oldest,
            last_activity_at__lt=newest,
        )
        .exclude(
            Q(active_cart__status=Cart.Status.AWAITING_PAYMENT)
            | Q(active_cart__status=Cart.Status.AWAITING_PHOTO),
        )
        .select_related("active_cart", "tenant")
    )


def process_inactivity_followup_for_session(
    session: ChatSession,
    *,
    dry_run: bool = False,
) -> bool:
    """
    Envia encerramento e reseta sessão. Retorna True se mensagem foi enviada (ou simulada).
    """
    if session_excluded_from_inactivity(session):
        return False

    resident = resolve_resident_for_session(session)
    market_name = ""
    resident_name = resident_first_name_from_string(session.temporary_name)
    if resident:
        resident_name = resident_display_name(resident)
        if resident.market_id and resident.market:
            market_name = resident.market.name or ""

    instance = resolve_whatsapp_instance(session.tenant_id)
    if instance is None:
        logger.warning(
            "Inatividade: sem WhatsApp ativo tenant=%s session=%s",
            session.tenant_id,
            session.pk,
        )
        return False

    message = build_inactivity_closing_message(
        resident_name=resident_name,
        market_name=market_name,
    )

    if dry_run:
        logger.info(
            "[dry-run] Encerraria sessão %s phone=%s: %s",
            session.pk,
            session.phone_number,
            message[:60],
        )
        return True

    with tenant_scope(session.tenant_id):
        send_whatsapp_reply(
            instance,
            session.phone_number,
            message,
            session=session,
            log_message=True,
        )
        if resident:
            cancel_open_carts_for_resident(resident)
        reset_chat_session_after_inactivity(session)

    return True


def process_inactivity_followups(
    *,
    min_idle_minutes: int = DEFAULT_MIN_IDLE_MINUTES,
    max_idle_minutes: int = DEFAULT_MAX_IDLE_MINUTES,
    dry_run: bool = False,
) -> InactivityFollowupResult:
    result = InactivityFollowupResult()
    qs = queryset_stale_sessions(
        min_idle_minutes=min_idle_minutes,
        max_idle_minutes=max_idle_minutes,
    )

    for session in qs.iterator():
        result.scanned += 1
        if session_excluded_from_inactivity(session):
            result.skipped += 1
            continue
        try:
            if process_inactivity_followup_for_session(session, dry_run=dry_run):
                result.sent += 1
            else:
                result.skipped += 1
        except Exception:
            result.errors += 1
            logger.exception(
                "Falha ao encerrar sessão por inatividade: session=%s tenant=%s",
                session.pk,
                session.tenant_id,
            )

    logger.info(
        "Inatividade: scanned=%s sent=%s skipped=%s errors=%s dry_run=%s",
        result.scanned,
        result.sent,
        result.skipped,
        result.errors,
        dry_run,
    )
    return result

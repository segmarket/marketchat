"""Criação e consulta de notificações do painel."""

from __future__ import annotations

from datetime import timedelta

from django.utils import timezone

from apps.notifications.models import Notification
from apps.residents.models import Resident
from apps.sales.services.intent_gatekeeper import MAINTENANCE_ISSUE, PAYMENT_ERROR
from apps.sales.services.resident_ai_context import resident_display_name, resident_market_name

DEDUP_WINDOW = timedelta(minutes=2)

CRITICAL_INTENTS = frozenset({MAINTENANCE_ISSUE, PAYMENT_ERROR})


def _truncate_message(text: str, limit: int = 200) -> str:
    cleaned = (text or "").strip()
    if len(cleaned) <= limit:
        return cleaned
    return f"{cleaned[: limit - 1]}…"


def _build_copy(
    *,
    intent_type: str,
    resident: Resident,
    original_message: str,
) -> tuple[str, str]:
    name = resident_display_name(resident)
    market = resident_market_name(resident)
    excerpt = _truncate_message(original_message)

    if intent_type == PAYMENT_ERROR:
        title = "Erro de pagamento"
        message = (
            f"{name} relatou um problema de pagamento no mercado {market}."
            + (f' Mensagem: "{excerpt}"' if excerpt else "")
        )
    elif intent_type == MAINTENANCE_ISSUE:
        title = "Problema de manutenção"
        message = (
            f"{name} relatou um problema estrutural no mercado {market}."
            + (f' Mensagem: "{excerpt}"' if excerpt else "")
        )
    else:
        title = "Incidente crítico"
        message = (
            f"{name} relatou um incidente no mercado {market}."
            + (f' Mensagem: "{excerpt}"' if excerpt else "")
        )

    return title, message


def create_critical_panel_notification(
    *,
    tenant_id: int,
    resident: Resident,
    intent_type: str,
    original_message: str,
) -> Notification | None:
    """
    Persiste alerta CRITICAL no painel quando o gatekeeper trata incidente.
    Retorna None se intent não for crítico ou deduplicação recente bloquear.
    """
    if intent_type not in CRITICAL_INTENTS:
        return None

    market = resident.market if resident.market_id else None
    since = timezone.now() - DEDUP_WINDOW
    duplicate = Notification.all_objects.filter(
        tenant_id=tenant_id,
        is_read=False,
        intent_type=intent_type,
        market_id=resident.market_id,
        created_at__gte=since,
    ).exists()
    if duplicate:
        return None

    title, message = _build_copy(
        intent_type=intent_type,
        resident=resident,
        original_message=original_message,
    )

    return Notification.all_objects.create(
        tenant_id=tenant_id,
        market=market,
        title=title,
        message=message,
        severity=Notification.Severity.CRITICAL,
        is_read=False,
        intent_type=intent_type,
    )

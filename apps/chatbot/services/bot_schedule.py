"""Verificação de horário comercial (pausa do bot)."""

from __future__ import annotations

from datetime import datetime, time
from typing import TYPE_CHECKING

from django.utils import timezone

if TYPE_CHECKING:
    from apps.chatbot.models import BotSchedule


def default_schedule_slots() -> list[dict]:
    """7 dias em memória (não persistidos) para UI inicial."""
    return [
        {
            "day_of_week": day,
            "is_active": False,
            "start_time": "09:00:00",
            "end_time": "18:00:00",
        }
        for day in range(7)
    ]


def serialize_schedule_row(row: BotSchedule) -> dict:
    return {
        "day_of_week": row.day_of_week,
        "is_active": row.is_active,
        "start_time": row.start_time.strftime("%H:%M:%S"),
        "end_time": row.end_time.strftime("%H:%M:%S"),
    }


def list_bot_schedule(tenant_id: int) -> list[dict]:
    from apps.chatbot.models import BotSchedule

    rows = list(
        BotSchedule.objects.filter(tenant_id=tenant_id).order_by("day_of_week"),
    )
    if not rows:
        return default_schedule_slots()
    return [serialize_schedule_row(row) for row in rows]


def should_bot_auto_reply(tenant_id: int, *, now: datetime | None = None) -> bool:
    """
    True se o bot deve responder automaticamente no instante atual.

    Os horários em BotSchedule são a janela humana (expediente):
    - sem registros → bot sempre responde (compatibilidade)
    - dia inativo (folga) → bot responde 24h
    - dia ativo e hora dentro de start–end → bot pausado (False)
    - dia ativo e hora fora da janela → bot responde
    """
    from apps.chatbot.models import BotSchedule

    has_any = BotSchedule.objects.filter(tenant_id=tenant_id).exists()
    if not has_any:
        return True

    current = now or timezone.localtime()
    if timezone.is_aware(current):
        current = timezone.localtime(current)
    day = current.weekday()  # Mon=0 … Sun=6
    current_time: time = current.time().replace(microsecond=0)

    row = (
        BotSchedule.objects.filter(tenant_id=tenant_id, day_of_week=day)
        .only("is_active", "start_time", "end_time")
        .first()
    )
    if row is None or not row.is_active:
        return True

    start = row.start_time
    end = row.end_time
    if start <= current_time <= end:
        return False
    return True

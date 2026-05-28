"""Métricas agregadas do chatbot para central de monitoramento."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Any

from django.db.models import Count, Max, Min, Q
from django.db.models.functions import TruncDate
from django.utils import timezone

from apps.chatbot.models import ChatMessageLog
from apps.chatbot.services.chat_logs_query import INTENT_RANK_CASE, RANK_TO_INTENT
from apps.residents.models import ChatSession, Resident
from apps.sales.models import Cart

INACTIVITY_MESSAGE_SNIPPET = "encerrando nosso atendimento"

CRITICAL_INTENTS = frozenset(
    {
        ChatMessageLog.IntentType.MAINTENANCE_ISSUE,
        ChatMessageLog.IntentType.PAYMENT_ERROR,
    },
)

AUTOMATED_INTENTS = frozenset(
    {
        ChatMessageLog.IntentType.PURCHASE,
        ChatMessageLog.IntentType.STOCK_ISSUE,
        ChatMessageLog.IntentType.GENERAL,
    },
)

STABILITY_UNASSIGNED_MARKET_LABEL = "Sem mercado"

HOURLY_BUCKETS: tuple[tuple[str, range], ...] = (
    ("00h-06h", range(0, 6)),
    ("06h-12h", range(6, 12)),
    ("12h-18h", range(12, 18)),
    ("18h-00h", range(18, 24)),
)


@dataclass
class AnalyticsFilters:
    tenant_id: int
    market_id: int | None = None


@dataclass
class AnalyticsCards:
    total_interactions: int
    total_interactions_change_pct: float
    critical_incidents: int
    critical_incidents_change_pct: float


@dataclass
class AnalyticsRetention:
    retention_rate: float
    automated_sessions_count: int
    support_tickets_count: int
    cancelled_sessions_count: int


@dataclass
class HourlyBucket:
    label: str
    count: int


@dataclass
class StabilityDayPoint:
    date: str
    counts_by_market: dict[str, int] = field(default_factory=dict)


@dataclass
class ChatbotAnalyticsPayload:
    cards: AnalyticsCards
    retention: AnalyticsRetention
    hourly_distribution: list[HourlyBucket] = field(default_factory=list)
    stability_series: list[StabilityDayPoint] = field(default_factory=list)
    stability_market_names: list[str] = field(default_factory=list)


def parse_market_id(query_params: Any) -> int | None:
    raw = query_params.get("market_id")
    if raw in (None, ""):
        return None
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


def _pct_change(current: int, previous: int) -> float:
    if previous == 0:
        return 0.0
    return round((current - previous) / previous * 100, 2)


def _base_logs_qs(filters: AnalyticsFilters):
    qs = ChatMessageLog.all_objects.filter(tenant_id=filters.tenant_id)
    if filters.market_id:
        qs = qs.filter(market_id=filters.market_id)
    return qs


def _comparable_previous_range(today: date) -> tuple[date, date]:
    """Mesmo intervalo de dias no mês calendário anterior (ex.: 1–17 mai → 1–17 abr)."""
    if today.month == 1:
        prev_month_start = date(today.year - 1, 12, 1)
    else:
        prev_month_start = date(today.year, today.month - 1, 1)

    try:
        prev_end = prev_month_start.replace(day=today.day)
    except ValueError:
        # Último dia do mês anterior se o dia não existir (ex.: 31 → 30)
        if prev_month_start.month == 12:
            next_month = date(prev_month_start.year + 1, 1, 1)
        else:
            next_month = date(prev_month_start.year, prev_month_start.month + 1, 1)
        prev_end = next_month - timedelta(days=1)
    else:
        prev_end = prev_month_start.replace(day=today.day)

    return prev_month_start, prev_end


def _current_month_range(today: date) -> tuple[date, date]:
    return date(today.year, today.month, 1), today


def _dominant_intent_from_rank(rank: int) -> str:
    return RANK_TO_INTENT.get(rank or 0, ChatMessageLog.IntentType.GENERAL)


def _attendance_groups_qs(qs, date_from: date, date_to: date):
    return (
        qs.filter(created_at__date__gte=date_from, created_at__date__lte=date_to)
        .annotate(attendance_day=TruncDate("created_at"))
        .values("session_id", "attendance_day")
        .annotate(
            dominant_rank=Max(INTENT_RANK_CASE),
            first_at=Min("created_at"),
        )
    )


def _count_interactions(qs, date_from: date, date_to: date) -> int:
    return qs.filter(
        created_at__date__gte=date_from,
        created_at__date__lte=date_to,
    ).count()


def _count_critical_incidents(groups: list[dict[str, Any]]) -> int:
    total = 0
    for row in groups:
        intent = _dominant_intent_from_rank(row.get("dominant_rank") or 0)
        if intent in CRITICAL_INTENTS:
            total += 1
    return total


def _is_cancelled_attendance(
    filters: AnalyticsFilters,
    session_id: int,
    attendance_day: date,
) -> bool:
    if ChatMessageLog.all_objects.filter(
        tenant_id=filters.tenant_id,
        session_id=session_id,
        created_at__date=attendance_day,
        direction=ChatMessageLog.Direction.OUTBOUND,
        message_text__icontains=INACTIVITY_MESSAGE_SNIPPET,
    ).exists():
        return True

    session = ChatSession.objects.filter(
        tenant_id=filters.tenant_id,
        pk=session_id,
    ).first()
    if session is None:
        return False

    resident = Resident.objects.filter(
        tenant_id=filters.tenant_id,
        phone_number=session.phone_number,
    ).first()
    if resident is None:
        return False

    cart_qs = Cart.objects.filter(
        tenant_id=filters.tenant_id,
        resident_id=resident.id,
        status__in=[Cart.Status.CANCELLED, Cart.Status.EXPIRED],
        updated_at__date=attendance_day,
    )
    if filters.market_id:
        cart_qs = cart_qs.filter(resident__market_id=filters.market_id)
    return cart_qs.exists()


def _retention_from_groups(
    filters: AnalyticsFilters,
    groups: list[dict[str, Any]],
) -> AnalyticsRetention:
    total = len(groups)
    automated = 0
    support = 0
    cancelled = 0

    for row in groups:
        intent = _dominant_intent_from_rank(row.get("dominant_rank") or 0)
        if intent in AUTOMATED_INTENTS:
            automated += 1
        if intent in CRITICAL_INTENTS:
            support += 1

        attendance_day = row["attendance_day"]
        if hasattr(attendance_day, "date"):
            attendance_day = attendance_day.date()
        if _is_cancelled_attendance(
            filters,
            row["session_id"],
            attendance_day,
        ):
            cancelled += 1

    retention_rate = round(100 * automated / total, 2) if total > 0 else 0.0

    return AnalyticsRetention(
        retention_rate=retention_rate,
        automated_sessions_count=automated,
        support_tickets_count=support,
        cancelled_sessions_count=cancelled,
    )


def _hourly_distribution(
    filters: AnalyticsFilters,
    groups: list[dict[str, Any]],
) -> list[HourlyBucket]:
    counts = {label: 0 for label, _ in HOURLY_BUCKETS}
    tz = timezone.get_current_timezone()

    for row in groups:
        first_at = row.get("first_at")
        if first_at is None:
            continue
        if timezone.is_naive(first_at):
            first_at = timezone.make_aware(first_at, tz)
        hour = timezone.localtime(first_at).hour
        for label, hour_range in HOURLY_BUCKETS:
            if hour in hour_range:
                counts[label] += 1
                break

    return [HourlyBucket(label=label, count=counts[label]) for label, _ in HOURLY_BUCKETS]


def _market_label_from_row(market_name: str | None) -> str:
    cleaned = (market_name or "").strip()
    return cleaned or STABILITY_UNASSIGNED_MARKET_LABEL


def _stability_series_by_market(
    qs,
    today: date,
) -> tuple[list[StabilityDayPoint], list[str]]:
    start = today - timedelta(days=29)
    end = today

    rows = (
        qs.filter(created_at__date__gte=start, created_at__date__lte=end)
        .annotate(day=TruncDate("created_at"))
        .values("day", "market__name")
        .annotate(count=Count("id"))
    )

    counts_by_day: dict[date, dict[str, int]] = {}
    market_names: set[str] = set()
    for row in rows:
        day_value = row["day"]
        if day_value is None:
            continue
        label = _market_label_from_row(row.get("market__name"))
        market_names.add(label)
        day_bucket = counts_by_day.setdefault(day_value, {})
        day_bucket[label] = day_bucket.get(label, 0) + int(row["count"] or 0)

    ordered_markets = sorted(market_names)
    points: list[StabilityDayPoint] = []
    for offset in range(30):
        day = start + timedelta(days=offset)
        day_counts = counts_by_day.get(day, {})
        points.append(
            StabilityDayPoint(
                date=day.isoformat(),
                counts_by_market={
                    name: day_counts.get(name, 0) for name in ordered_markets
                },
            ),
        )

    return points, ordered_markets


def compute_chatbot_analytics(filters: AnalyticsFilters) -> ChatbotAnalyticsPayload:
    today = timezone.localdate()
    month_start, month_end = _current_month_range(today)
    prev_start, prev_end = _comparable_previous_range(today)

    base_qs = _base_logs_qs(filters)

    total_current = _count_interactions(base_qs, month_start, month_end)
    total_prev = _count_interactions(base_qs, prev_start, prev_end)

    groups_current = list(_attendance_groups_qs(base_qs, month_start, month_end))
    groups_prev = list(_attendance_groups_qs(base_qs, prev_start, prev_end))

    critical_current = _count_critical_incidents(groups_current)
    critical_prev = _count_critical_incidents(groups_prev)

    cards = AnalyticsCards(
        total_interactions=total_current,
        total_interactions_change_pct=_pct_change(total_current, total_prev),
        critical_incidents=critical_current,
        critical_incidents_change_pct=_pct_change(critical_current, critical_prev),
    )

    retention = _retention_from_groups(filters, groups_current)
    hourly = _hourly_distribution(filters, groups_current)
    stability, stability_markets = _stability_series_by_market(base_qs, today)

    return ChatbotAnalyticsPayload(
        cards=cards,
        retention=retention,
        hourly_distribution=hourly,
        stability_series=stability,
        stability_market_names=stability_markets,
    )

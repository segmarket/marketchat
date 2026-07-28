"""Consultas agrupadas para central de atendimento (sessão + dia)."""

from __future__ import annotations

from datetime import date
from typing import Any

from django.core.paginator import Paginator
from django.db.models import Case, Count, IntegerField, Max, Q, Value, When
from django.db.models.functions import TruncDate
from django.utils import timezone

from apps.chatbot.models import ChatMessageLog
from apps.chatbot.services.chat_logging import pick_dominant_intent
from apps.billing.services.tenant_default_asaas_customer import resident_billing_identified
from apps.residents.models import ChatSession, Resident

INTENT_RANK_CASE = Case(
    When(
        intent_type=ChatMessageLog.IntentType.MAINTENANCE_ISSUE,
        then=Value(6),
    ),
    When(
        intent_type=ChatMessageLog.IntentType.COMPLAINT,
        then=Value(5),
    ),
    When(
        intent_type=ChatMessageLog.IntentType.PAYMENT_ERROR,
        then=Value(4),
    ),
    When(
        intent_type=ChatMessageLog.IntentType.STOCK_ISSUE,
        then=Value(3),
    ),
    When(
        intent_type=ChatMessageLog.IntentType.PURCHASE,
        then=Value(2),
    ),
    When(intent_type=ChatMessageLog.IntentType.GENERAL, then=Value(1)),
    default=Value(0),
    output_field=IntegerField(),
)

RANK_TO_INTENT: dict[int, str] = {
    6: ChatMessageLog.IntentType.MAINTENANCE_ISSUE,
    5: ChatMessageLog.IntentType.COMPLAINT,
    4: ChatMessageLog.IntentType.PAYMENT_ERROR,
    3: ChatMessageLog.IntentType.STOCK_ISSUE,
    2: ChatMessageLog.IntentType.PURCHASE,
    1: ChatMessageLog.IntentType.GENERAL,
}


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value.strip()[:10])
    except ValueError:
        return None


def _digits_only(value: str | None) -> str:
    return "".join(c for c in (value or "") if c.isdigit())


def filter_logs_queryset(
    tenant_id: int,
    *,
    resident_name: str = "",
    phone: str = "",
    attendance_date: date | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    market_id: int | None = None,
    intent_type: str = "",
) -> Any:
    qs = ChatMessageLog.all_objects.filter(tenant_id=tenant_id)

    name = (resident_name or "").strip()
    if name:
        qs = qs.filter(resident__name__icontains=name)

    phone_digits = _digits_only(phone)
    if phone_digits:
        qs = qs.filter(
            Q(resident__phone_number__icontains=phone_digits)
            | Q(session__phone_number__icontains=phone_digits),
        )

    if attendance_date:
        qs = qs.filter(created_at__date=attendance_date)
    else:
        if date_from:
            qs = qs.filter(created_at__date__gte=date_from)
        if date_to:
            qs = qs.filter(created_at__date__lte=date_to)

    if market_id:
        qs = qs.filter(market_id=market_id)

    intent = (intent_type or "").strip().upper()
    if intent and intent in ChatMessageLog.IntentType.values:
        qs = qs.filter(intent_type=intent)

    return qs


def grouped_attendance_queryset(qs: Any) -> Any:
    return (
        qs.annotate(attendance_day=TruncDate("created_at"))
        .values("session_id", "attendance_day")
        .annotate(
            last_at=Max("created_at"),
            message_count=Count("id"),
            dominant_rank=Max(INTENT_RANK_CASE),
        )
        .order_by("-last_at")
    )


def paginate_grouped(
    groups_qs: Any,
    *,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[dict[str, Any]], int]:
    paginator = Paginator(groups_qs, page_size)
    page_obj = paginator.get_page(page)
    return list(page_obj.object_list), paginator.count


def _preview_for_group(
    tenant_id: int,
    session_id: int,
    attendance_day: date,
) -> str:
    log = (
        ChatMessageLog.all_objects.filter(
            tenant_id=tenant_id,
            session_id=session_id,
            created_at__date=attendance_day,
            direction=ChatMessageLog.Direction.INBOUND,
        )
        .order_by("-created_at")
        .values_list("message_text", flat=True)
        .first()
    )
    text = (log or "").strip()
    if len(text) > 120:
        return text[:117] + "..."
    return text


def _resident_info_for_group(
    tenant_id: int,
    session_id: int,
    attendance_day: date,
    session: ChatSession | None,
) -> tuple[str, str, str]:
    log = (
        ChatMessageLog.all_objects.filter(
            tenant_id=tenant_id,
            session_id=session_id,
            created_at__date=attendance_day,
        )
        .select_related("resident", "market")
        .order_by("-created_at")
        .first()
    )
    if log and log.resident:
        return (
            log.resident.name or "",
            log.resident.phone_number or session.phone_number if session else "",
            log.market.name if log.market else "",
        )
    if session:
        return ("", session.phone_number, "")
    return ("", "", "")


def build_attendance_rows(
    tenant_id: int,
    group_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    if not group_rows:
        return []

    session_ids = {row["session_id"] for row in group_rows}
    sessions = {
        s.id: s
        for s in ChatSession.objects.filter(
            tenant_id=tenant_id,
            id__in=session_ids,
        )
    }

    results: list[dict[str, Any]] = []
    for row in group_rows:
        session_id = row["session_id"]
        attendance_day = row["attendance_day"]
        session = sessions.get(session_id)
        resident_name, resident_phone, market_name = _resident_info_for_group(
            tenant_id,
            session_id,
            attendance_day,
            session,
        )

        rank = row.get("dominant_rank") or 0
        dominant = RANK_TO_INTENT.get(rank, ChatMessageLog.IntentType.GENERAL)

        # Refinar com pick_dominant_intent se houver empate em rank 0
        if rank == 0:
            intents = list(
                ChatMessageLog.all_objects.filter(
                    tenant_id=tenant_id,
                    session_id=session_id,
                    created_at__date=attendance_day,
                )
                .exclude(intent_type="")
                .values_list("intent_type", flat=True),
            )
            if intents:
                dominant = pick_dominant_intent(intents)

        results.append(
            {
                "session_id": session_id,
                "attendance_date": attendance_day.isoformat()
                if hasattr(attendance_day, "isoformat")
                else str(attendance_day),
                "resident_name": resident_name,
                "resident_phone": resident_phone,
                "market_name": market_name,
                "intent_type": dominant,
                "last_at": row["last_at"],
                "message_count": row["message_count"],
                "preview": _preview_for_group(tenant_id, session_id, attendance_day),
            },
        )
    return results


def parse_list_params(query_params: Any) -> dict[str, Any]:
    return {
        "resident_name": (query_params.get("resident_name") or "").strip(),
        "phone": (query_params.get("phone") or "").strip(),
        "attendance_date": _parse_date(query_params.get("date")),
        "date_from": _parse_date(query_params.get("date_from")),
        "date_to": _parse_date(query_params.get("date_to")),
        "market_id": _parse_int(query_params.get("market_id")),
        "intent_type": (query_params.get("intent_type") or "").strip(),
        "page": _parse_int(query_params.get("page")) or 1,
    }


def _parse_int(value: Any) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def conversation_messages(
    tenant_id: int,
    *,
    session_id: int,
    attendance_date: date | None = None,
    after_id: int | None = None,
    limit: int = 200,
) -> tuple[dict[str, Any], list[ChatMessageLog]]:
    qs = ChatMessageLog.all_objects.filter(
        tenant_id=tenant_id,
        session_id=session_id,
    ).select_related("resident", "market", "cart", "session")
    if attendance_date:
        qs = qs.filter(created_at__date=attendance_date)
    if after_id is not None and after_id > 0:
        qs = qs.filter(id__gt=after_id)

    if after_id is not None and after_id > 0:
        logs = list(qs.order_by("created_at", "id")[:limit])
    else:
        # Últimas N mensagens em ordem cronológica.
        recent = list(qs.order_by("-created_at", "-id")[:limit])
        logs = list(reversed(recent))

    session = logs[0].session if logs else None
    if session is None:
        session = (
            ChatSession.objects.filter(tenant_id=tenant_id, pk=session_id).first()
        )
    if session is None:
        return {}, []

    header_date = attendance_date
    if header_date is None and logs:
        header_date = timezone.localdate(logs[0].created_at)

    resident_name = ""
    market_name = ""
    if logs:
        for log in reversed(logs):
            if log.resident:
                resident_name = log.resident.name or resident_name
                if log.market:
                    market_name = log.market.name
                break
    if not resident_name:
        # Busca nome no histórico completo / residente quando after_id não traz logs.
        name_log = (
            ChatMessageLog.all_objects.filter(
                tenant_id=tenant_id,
                session_id=session_id,
                resident__isnull=False,
            )
            .select_related("resident", "market")
            .order_by("-created_at")
            .first()
        )
        if name_log and name_log.resident:
            resident_name = name_log.resident.name or ""
            if name_log.market:
                market_name = name_log.market.name
        if not resident_name:
            resident_name = session.temporary_name or ""

    billing_resident = (
        Resident.objects.filter(
            tenant_id=tenant_id,
            phone_number=session.phone_number,
            is_active=True,
            is_anonymized=False,
        )
        .select_related("market")
        .first()
    )
    identified = (
        resident_billing_identified(billing_resident)
        if billing_resident is not None
        else False
    )

    header = {
        "session_id": session_id,
        "resident_name": resident_name,
        "resident_phone": session.phone_number,
        "market_name": market_name,
        "attendance_date": header_date.isoformat() if header_date else "",
        "is_bot_active": session.is_bot_active,
        "resident_billing_identified": identified,
        "last_human_interaction_at": (
            session.last_human_interaction_at.isoformat()
            if session.last_human_interaction_at
            else None
        ),
    }
    return header, logs

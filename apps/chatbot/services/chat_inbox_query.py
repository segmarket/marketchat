"""Listagem de sessões para o inbox de atendimento (Master-Detail)."""

from __future__ import annotations

from typing import Any

from django.core.paginator import Paginator
from django.db.models import Max, OuterRef, Q, Subquery

from apps.chatbot.models import ChatMessageLog
from apps.residents.models import ChatSession, Resident


def _digits_only(value: str | None) -> str:
    return "".join(c for c in (value or "") if c.isdigit())


def _preview_text(text: str | None) -> str:
    value = (text or "").strip()
    if len(value) > 120:
        return value[:117] + "..."
    return value


def list_inbox_sessions(
    tenant_id: int,
    *,
    bot_active: bool | None = None,
    q: str = "",
    page: int = 1,
    page_size: int = 50,
) -> tuple[list[dict[str, Any]], int]:
    """
    Retorna linhas do inbox ordenadas pela última mensagem.

    Evita N+1: anota last_message_at / last_log_id e carrega logs em lote.
    """
    latest_log_id = (
        ChatMessageLog.all_objects.filter(
            tenant_id=tenant_id,
            session_id=OuterRef("pk"),
        )
        .order_by("-created_at", "-id")
        .values("id")[:1]
    )

    qs = (
        ChatSession.objects.filter(tenant_id=tenant_id)
        .annotate(
            last_message_at=Max("message_logs__created_at"),
            last_log_id=Subquery(latest_log_id),
        )
        .filter(last_message_at__isnull=False)
    )

    if bot_active is True:
        qs = qs.filter(is_bot_active=True)
    elif bot_active is False:
        qs = qs.filter(is_bot_active=False)

    query = (q or "").strip()
    if query:
        digits = _digits_only(query)
        name_q = Q(temporary_name__icontains=query) | Q(
            message_logs__resident__name__icontains=query,
        )
        if digits:
            name_q |= Q(phone_number__icontains=digits) | Q(
                message_logs__resident__phone_number__icontains=digits,
            )
        qs = qs.filter(name_q).distinct()

    qs = qs.order_by("-last_message_at", "-id")
    paginator = Paginator(qs, page_size)
    page_obj = paginator.get_page(max(1, page))
    sessions = list(page_obj.object_list)
    if not sessions:
        return [], paginator.count

    session_ids = [s.id for s in sessions]
    log_ids = [s.last_log_id for s in sessions if s.last_log_id]

    log_by_session = {
        log.session_id: log
        for log in ChatMessageLog.all_objects.filter(id__in=log_ids).select_related(
            "resident",
            "market",
        )
    }

    inbound_ids = {
        row["session_id"]: row["last_inbound_id"]
        for row in ChatMessageLog.all_objects.filter(
            tenant_id=tenant_id,
            session_id__in=session_ids,
            direction=ChatMessageLog.Direction.INBOUND,
        )
        .values("session_id")
        .annotate(last_inbound_id=Max("id"))
    }

    phones = [s.phone_number for s in sessions]
    residents = {
        r.phone_number: r
        for r in Resident.objects.filter(
            tenant_id=tenant_id,
            phone_number__in=phones,
            is_active=True,
            is_anonymized=False,
        ).select_related("market")
    }

    rows: list[dict[str, Any]] = []
    for session in sessions:
        log = log_by_session.get(session.id)
        resident = None
        if log and log.resident_id:
            resident = log.resident
        if resident is None:
            resident = residents.get(session.phone_number)

        resident_name = ""
        market_name = ""
        if resident:
            resident_name = resident.name or ""
            if resident.market_id and resident.market:
                market_name = resident.market.name
        if not resident_name:
            resident_name = session.temporary_name or ""
        if not market_name and log and log.market_id and log.market:
            market_name = log.market.name

        rows.append(
            {
                "session_id": session.id,
                "resident_name": resident_name,
                "resident_phone": session.phone_number,
                "market_name": market_name,
                "is_bot_active": session.is_bot_active,
                "last_at": session.last_message_at,
                "preview": _preview_text(log.message_text if log else ""),
                "last_direction": log.direction if log else "",
                "last_inbound_id": inbound_ids.get(session.id),
            },
        )

    return rows, paginator.count


def parse_bot_active_param(raw: str | None) -> bool | None:
    if raw is None or raw == "":
        return None
    value = raw.strip().lower()
    if value in ("1", "true", "yes"):
        return True
    if value in ("0", "false", "no"):
        return False
    return None

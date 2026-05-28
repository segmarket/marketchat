from __future__ import annotations

from typing import Any

from apps.chatbot.services.chatbot_analytics import ChatbotAnalyticsPayload


def serialize_chatbot_analytics(payload: ChatbotAnalyticsPayload) -> dict[str, Any]:
    return {
        "cards": {
            "total_interactions": payload.cards.total_interactions,
            "total_interactions_change_pct": payload.cards.total_interactions_change_pct,
            "critical_incidents": payload.cards.critical_incidents,
            "critical_incidents_change_pct": payload.cards.critical_incidents_change_pct,
        },
        "retention": {
            "retention_rate": payload.retention.retention_rate,
            "automated_sessions_count": payload.retention.automated_sessions_count,
            "support_tickets_count": payload.retention.support_tickets_count,
            "cancelled_sessions_count": payload.retention.cancelled_sessions_count,
        },
        "hourly_distribution": [
            {"label": bucket.label, "count": bucket.count}
            for bucket in payload.hourly_distribution
        ],
        "stability_market_names": list(payload.stability_market_names),
        "stability_series": [
            {"date": point.date, **point.counts_by_market}
            for point in payload.stability_series
        ],
    }

"""Meta Conversions API (CAPI) — Purchase server-side (delega a FacebookCAPI)."""

from __future__ import annotations

from typing import Any

from apps.billing.services.facebook_capi import FacebookCAPI, schedule_facebook_capi_event


def send_meta_purchase_event(
    user_email: str,
    user_phone: str,
    value: float,
    currency: str = "BRL",
    *,
    event_id: str | None = None,
) -> None:
    """Envia evento Purchase para a Graph API."""
    FacebookCAPI().send_event(
        "Purchase",
        user_email,
        user_phone,
        custom_data={
            "value": float(value),
            "currency": currency or "BRL",
        },
        event_id=event_id,
    )


def schedule_meta_purchase_event(
    user_email: str,
    user_phone: str,
    value: float,
    currency: str = "BRL",
    *,
    event_id: str | None = None,
) -> None:
    """Agenda envio Purchase em background após commit da transação."""
    schedule_facebook_capi_event(
        event_name="Purchase",
        user_email=user_email,
        user_phone=user_phone,
        custom_data={
            "value": float(value),
            "currency": currency or "BRL",
        },
        event_id=event_id,
    )

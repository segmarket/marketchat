"""Meta Conversions API (CAPI) — eventos server-side (Purchase)."""

from __future__ import annotations

import hashlib
import logging
import threading
import time
from typing import Any

import requests
from django.conf import settings
from django.db import transaction

logger = logging.getLogger(__name__)

GRAPH_API_VERSION = "v19.0"
REQUEST_TIMEOUT_SECONDS = 8


def _sha256_normalize(value: str) -> str:
    normalized = (value or "").strip().lower()
    if not normalized:
        return ""
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _normalize_phone(phone: str) -> str:
    digits = "".join(c for c in (phone or "") if c.isdigit())
    if not digits:
        return ""
    if len(digits) in (10, 11):
        digits = f"55{digits}"
    return digits


def _hash_email(email: str) -> str:
    return _sha256_normalize(email)


def _hash_phone(phone: str) -> str:
    digits = _normalize_phone(phone)
    if not digits:
        return ""
    return hashlib.sha256(digits.encode("utf-8")).hexdigest()


def send_meta_purchase_event(
    user_email: str,
    user_phone: str,
    value: float,
    currency: str = "BRL",
    *,
    event_id: str | None = None,
) -> None:
    """
    Envia evento Purchase para a Graph API.
    Falhas de rede/config são logadas e não propagadas.
    """
    pixel_id = (getattr(settings, "META_PIXEL_ID", None) or "").strip()
    access_token = (getattr(settings, "META_ACCESS_TOKEN", None) or "").strip()
    if not pixel_id or not access_token:
        logger.debug("Meta CAPI ignorado: META_PIXEL_ID ou META_ACCESS_TOKEN ausente")
        return

    user_data: dict[str, Any] = {}
    em = _hash_email(user_email)
    ph = _hash_phone(user_phone)
    if em:
        user_data["em"] = [em]
    if ph:
        user_data["ph"] = [ph]

    event: dict[str, Any] = {
        "event_name": "Purchase",
        "event_time": int(time.time()),
        "action_source": "website",
        "user_data": user_data,
        "custom_data": {
            "value": float(value),
            "currency": currency or "BRL",
        },
    }
    if event_id:
        event["event_id"] = str(event_id)

    url = f"https://graph.facebook.com/{GRAPH_API_VERSION}/{pixel_id}/events"
    try:
        response = requests.post(
            url,
            params={"access_token": access_token},
            json={"data": [event]},
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        if response.status_code >= 400:
            logger.warning(
                "Meta CAPI Purchase HTTP %s: %s",
                response.status_code,
                (response.text or "")[:300],
            )
    except requests.RequestException as exc:
        logger.warning("Meta CAPI Purchase falhou: %s", exc)


def schedule_meta_purchase_event(
    user_email: str,
    user_phone: str,
    value: float,
    currency: str = "BRL",
    *,
    event_id: str | None = None,
) -> None:
    """Agenda envio em thread daemon após commit da transação (não bloqueia o webhook)."""

    def _run() -> None:
        try:
            send_meta_purchase_event(
                user_email,
                user_phone,
                value,
                currency,
                event_id=event_id,
            )
        except Exception:
            logger.exception("Meta CAPI Purchase: erro inesperado em background")

    def _start_thread() -> None:
        threading.Thread(target=_run, daemon=True, name="meta-capi-purchase").start()

    try:
        transaction.on_commit(_start_thread)
    except Exception:
        # Fora de transação atômica: dispara imediatamente em background.
        _start_thread()

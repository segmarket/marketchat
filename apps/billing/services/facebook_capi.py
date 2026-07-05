"""Meta / Facebook Conversions API (CAPI) — envio genérico server-side."""

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


class FacebookCAPI:
    GRAPH_API_VERSION = "v20.0"

    def __init__(
        self,
        pixel_id: str | None = None,
        access_token: str | None = None,
    ) -> None:
        self.pixel_id = (pixel_id or getattr(settings, "META_PIXEL_ID", None) or "").strip()
        self.access_token = (
            access_token or getattr(settings, "META_ACCESS_TOKEN", None) or ""
        ).strip()

    def send_event(
        self,
        event_name: str,
        user_email: str,
        user_phone: str,
        custom_data: dict[str, Any] | None = None,
        *,
        event_id: str | None = None,
        action_source: str = "website",
    ) -> bool:
        """
        Envia um evento para a Graph API.
        Retorna True em sucesso HTTP 2xx; False se ignorado ou falha (nunca propaga).
        """
        if not self.pixel_id or not self.access_token:
            logger.debug(
                "Facebook CAPI ignorado: META_PIXEL_ID ou META_ACCESS_TOKEN ausente"
            )
            return False

        user_data: dict[str, Any] = {}
        em = _hash_email(user_email)
        ph = _hash_phone(user_phone)
        if em:
            user_data["em"] = [em]
        if ph:
            user_data["ph"] = [ph]

        event: dict[str, Any] = {
            "event_name": event_name,
            "event_time": int(time.time()),
            "action_source": action_source,
            "user_data": user_data,
        }
        if custom_data:
            event["custom_data"] = custom_data
        if event_id:
            event["event_id"] = str(event_id)

        url = (
            f"https://graph.facebook.com/{self.GRAPH_API_VERSION}/"
            f"{self.pixel_id}/events"
        )
        try:
            response = requests.post(
                url,
                params={"access_token": self.access_token},
                json={"data": [event]},
                timeout=REQUEST_TIMEOUT_SECONDS,
            )
            if response.status_code >= 400:
                logger.warning(
                    "Facebook CAPI %s HTTP %s: %s",
                    event_name,
                    response.status_code,
                    (response.text or "")[:300],
                )
                return False
            return True
        except requests.RequestException as exc:
            logger.warning("Facebook CAPI %s falhou: %s", event_name, exc)
            return False


def schedule_facebook_capi_event(
    *,
    event_name: str,
    user_email: str,
    user_phone: str,
    custom_data: dict[str, Any] | None = None,
    event_id: str | None = None,
    action_source: str = "website",
) -> None:
    """Agenda envio em thread daemon após commit da transação (não bloqueia a request)."""

    def _run() -> None:
        try:
            FacebookCAPI().send_event(
                event_name,
                user_email,
                user_phone,
                custom_data,
                event_id=event_id,
                action_source=action_source,
            )
        except Exception:
            logger.exception("Facebook CAPI %s: erro inesperado em background", event_name)

    def _start_thread() -> None:
        threading.Thread(
            target=_run,
            daemon=True,
            name=f"facebook-capi-{event_name.lower()}",
        ).start()

    try:
        transaction.on_commit(_start_thread)
    except Exception:
        _start_thread()

"""Normalização do JSON enviado pelo webhook do Asaas."""

from __future__ import annotations

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)

CART_EXTERNAL_REF_PREFIX = "marketchat-cart-"


def parse_http_request_body(request) -> dict[str, Any]:
    """Lê o corpo POST (DRF request.data ou JSON bruto)."""
    data = getattr(request, "data", None)
    if isinstance(data, dict) and data:
        return data

    raw = getattr(request, "body", b"") or b""
    if not raw:
        return {}

    try:
        parsed = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        logger.warning("Webhook Asaas: corpo JSON inválido: %s", exc)
        return {}

    return parsed if isinstance(parsed, dict) else {}


def cart_external_reference(cart_id: int) -> str:
    return f"{CART_EXTERNAL_REF_PREFIX}{cart_id}"


def parse_cart_id_from_external_reference(value: str) -> int | None:
    ref = (value or "").strip()
    if not ref.startswith(CART_EXTERNAL_REF_PREFIX):
        return None
    try:
        return int(ref[len(CART_EXTERNAL_REF_PREFIX) :])
    except ValueError:
        return None


def normalize_asaas_webhook(payload: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    """
    Extrai (evento, payment) de formatos usados pelo Asaas v3.
    """
    event = (
        payload.get("event")
        or payload.get("type")
        or payload.get("action")
        or ""
    )
    event = str(event).strip().upper()

    payment = payload.get("payment")
    if isinstance(payment, dict):
        return event, payment

    # Alguns ambientes enviam a cobrança na raiz
    root_id = str(payload.get("id") or "").strip()
    if root_id.startswith("pay_"):
        return event, payload

    return event, {}

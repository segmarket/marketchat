from __future__ import annotations

import logging
import re
from typing import Any

import requests
from django.core.files.base import ContentFile

from apps.integrations.models import WhatsappInstance
from apps.integrations.services.evolution_client import EvolutionClient
from apps.sales.models import Cart

logger = logging.getLogger(__name__)

MAX_PHOTO_BYTES = 8 * 1024 * 1024
ALLOWED_CONTENT_TYPES = frozenset(
    {
        "image/jpeg",
        "image/jpg",
        "image/png",
        "image/webp",
        "image/gif",
    },
)
HTTP_URL_PATTERN = re.compile(r"^https?://", re.I)

# JPEG mínimo (SOI+EOI) — suficiente para a demo; sem Evolution.
_DEMO_PLACEHOLDER_JPEG = b"\xff\xd8\xff\xd9"


def _is_demo_simulated_image(raw_message: dict[str, Any], instance: WhatsappInstance) -> bool:
    from apps.demo.services.portal import DEMO_API_KEY

    if instance.api_key == DEMO_API_KEY:
        return True
    image_msg = raw_message.get("imageMessage")
    if isinstance(image_msg, dict) and image_msg.get("demoSimulated"):
        return True
    return False


def _extract_image_url_from_message(raw_message: dict[str, Any]) -> str:
    """Tenta obter URL direta de imagem no payload Evolution/WhatsApp."""
    if not isinstance(raw_message, dict):
        return ""

    def search(node: Any, depth: int = 0) -> str:
        if depth > 6:
            return ""
        if isinstance(node, str) and HTTP_URL_PATTERN.match(node):
            return node.strip()
        if not isinstance(node, dict):
            return ""
        for key in ("url", "directPath", "mediaUrl", "downloadUrl"):
            val = node.get(key)
            if isinstance(val, str) and HTTP_URL_PATTERN.match(val):
                return val.strip()
        for val in node.values():
            if isinstance(val, dict):
                found = search(val, depth + 1)
                if found:
                    return found
        return ""

    image_msg = raw_message.get("imageMessage")
    if isinstance(image_msg, dict):
        url = search(image_msg)
        if url:
            return url
    return search(raw_message)


def _validate_image_bytes(data: bytes, content_type: str = "") -> bool:
    if not data or len(data) > MAX_PHOTO_BYTES:
        return False
    if content_type:
        ct = content_type.split(";")[0].strip().lower()
        if ct and ct not in ALLOWED_CONTENT_TYPES and not ct.startswith("image/"):
            return False
    return True


def _download_image_via_url(url: str) -> bytes | None:
    try:
        response = requests.get(url, timeout=(5, 30), stream=True)
        response.raise_for_status()
        content_type = (response.headers.get("Content-Type") or "").lower()
        chunks: list[bytes] = []
        size = 0
        for chunk in response.iter_content(chunk_size=64 * 1024):
            if not chunk:
                continue
            size += len(chunk)
            if size > MAX_PHOTO_BYTES:
                logger.warning("URL de imagem excede tamanho máximo: %s", url[:80])
                return None
            chunks.append(chunk)
        data = b"".join(chunks)
        if not _validate_image_bytes(data, content_type):
            return None
        return data
    except Exception:
        logger.exception("Falha ao baixar imagem por URL: %s", url[:80])
        return None


def _download_image_via_evolution(
    *,
    instance: WhatsappInstance,
    raw_message: dict[str, Any],
) -> bytes | None:
    client = EvolutionClient()
    try:
        payload = client.download_media(
            instance_api_key=instance.api_key,
            message=raw_message,
        )
        data = client.extract_downloaded_media_bytes(payload)
    except Exception:
        logger.exception(
            "Falha ao baixar mídia Evolution: tenant=%s",
            instance.tenant_id,
        )
        return None
    if not _validate_image_bytes(data):
        return None
    return data


def download_security_photo_bytes(
    *,
    instance: WhatsappInstance,
    raw_message: dict[str, Any],
) -> bytes | None:
    """Baixa bytes da foto: Evolution API primeiro, fallback por URL no payload."""
    if _is_demo_simulated_image(raw_message, instance):
        return _DEMO_PLACEHOLDER_JPEG

    data = _download_image_via_evolution(instance=instance, raw_message=raw_message)
    if data:
        return data

    url = _extract_image_url_from_message(raw_message)
    if url:
        return _download_image_via_url(url)
    return None


def save_cart_photo_from_webhook(
    *,
    instance: WhatsappInstance,
    cart: Cart,
    raw_message: dict[str, Any],
    evolution_message_id: str = "",
) -> bool:
    """Baixa imagem e salva em cart.product_photo."""
    if not raw_message:
        return False

    data = download_security_photo_bytes(instance=instance, raw_message=raw_message)
    if not data:
        logger.warning("Mídia vazia após download: cart=%s", cart.id)
        return False

    filename = f"cart_{cart.id}.jpg"
    cart.product_photo.save(filename, ContentFile(data), save=True)

    from apps.chatbot.services.chat_logging import (
        get_or_create_chat_session,
        log_inbound_image_from_cart,
    )

    session = get_or_create_chat_session(
        instance.tenant_id,
        cart.resident.phone_number,
    )
    log_inbound_image_from_cart(
        tenant_id=instance.tenant_id,
        session=session,
        cart=cart,
        resident=cart.resident,
        evolution_message_id=evolution_message_id,
    )
    return True

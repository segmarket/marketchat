from __future__ import annotations

import logging
from typing import Any

from django.core.files.base import ContentFile

from apps.integrations.models import WhatsappInstance
from apps.integrations.services.evolution_client import EvolutionClient
from apps.sales.models import Cart

logger = logging.getLogger(__name__)


def save_cart_photo_from_webhook(
    *,
    instance: WhatsappInstance,
    cart: Cart,
    raw_message: dict[str, Any],
) -> bool:
    """Baixa imagem da Evolution e salva em cart.product_photo."""
    if not raw_message:
        return False

    client = EvolutionClient()

    try:
        payload = client.download_media(
            instance_api_key=instance.api_key,
            message=raw_message,
        )
        data = client.extract_downloaded_media_bytes(payload)
    except Exception:
        logger.exception(
            "Falha ao baixar mídia: tenant=%s cart=%s",
            instance.tenant_id,
            cart.id,
        )
        return False

    if not data:
        logger.warning("Mídia vazia após download: cart=%s", cart.id)
        return False

    filename = f"cart_{cart.id}.jpg"
    cart.product_photo.save(filename, ContentFile(data), save=True)
    return True

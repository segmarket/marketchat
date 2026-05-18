from __future__ import annotations

import logging

from apps.integrations.models import WhatsappInstance
from apps.integrations.services.evolution_client import EvolutionClient

logger = logging.getLogger(__name__)


def send_whatsapp_reply(instance: WhatsappInstance, phone: str, text: str) -> None:
    """Envia mensagem de texto via Evolution GO."""
    digits = "".join(c for c in phone if c.isdigit())
    if not digits or not text.strip():
        return
    client = EvolutionClient()
    try:
        client.send_text(
            instance_api_key=instance.api_key,
            number=digits,
            text=text,
        )
    except Exception:
        logger.exception(
            "Falha ao enviar WhatsApp: tenant=%s phone=%s",
            instance.tenant_id,
            digits,
        )
        raise

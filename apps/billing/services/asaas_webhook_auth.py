"""Validação de autenticidade das requisições de webhook do Asaas."""

from __future__ import annotations

import logging
import secrets

from django.conf import settings

from apps.billing.services.asaas_webhook_payload import extract_asaas_webhook_token

logger = logging.getLogger(__name__)

# ASAAS_WEBHOOK_TOKEN = authToken do webhook no painel Asaas (Integrações > Webhooks).
# NÃO use ASAAS_API_KEY ($aact_...) — o Asaas proíbe e não envia esse valor no webhook.


def verify_asaas_webhook_request(request) -> bool:
    """
    Valida o header oficial asaas-access-token quando ASAAS_WEBHOOK_VERIFY=True.
    """
    if not settings.ASAAS_WEBHOOK_VERIFY:
        return True

    expected = (settings.ASAAS_WEBHOOK_TOKEN or "").strip()
    if not expected:
        logger.warning(
            "Webhook Asaas rejeitado: ASAAS_WEBHOOK_TOKEN não configurado no servidor"
        )
        return False

    received = extract_asaas_webhook_token(request)
    if not received:
        logger.warning(
            "Webhook Asaas rejeitado: header asaas-access-token ausente"
        )
        return False

    if not secrets.compare_digest(
        received.encode("utf-8"),
        expected.encode("utf-8"),
    ):
        logger.warning("Tentativa de webhook fraudulento detectada")
        return False

    return True

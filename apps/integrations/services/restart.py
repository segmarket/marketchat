"""Reinício de sessão WhatsApp no Evolution GO."""

from __future__ import annotations

from apps.integrations.models import WhatsappInstance
from apps.integrations.services.evolution_client import EvolutionClient
from apps.integrations.services.instance_dashboard import sync_instance_from_evolution


class EvolutionRestartError(Exception):
    pass


def restart_whatsapp_instance(
    instance: WhatsappInstance,
    *,
    client: EvolutionClient | None = None,
) -> WhatsappInstance:
    client = client or EvolutionClient()
    try:
        client.restart_instance(
            instance_name=instance.instance_name,
            instance_api_key=instance.api_key,
        )
    except Exception as exc:
        raise EvolutionRestartError(str(exc)) from exc
    instance.connection_status = WhatsappInstance.ConnectionStatus.CONNECTING
    instance.save(update_fields=["connection_status", "updated_at"])
    return sync_instance_from_evolution(instance, client=client)

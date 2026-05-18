from __future__ import annotations

from django.utils import timezone


def greeting_for_now() -> str:
    """Saudação conforme horário local do servidor (America/Sao_Paulo)."""
    now = timezone.localtime()
    hour = now.hour
    if 5 <= hour <= 11:
        return "Bom dia"
    if 12 <= hour <= 17:
        return "Boa tarde"
    return "Boa noite"

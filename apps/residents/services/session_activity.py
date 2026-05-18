"""Atualização de atividade da sessão WhatsApp."""

from __future__ import annotations

from django.utils import timezone

from apps.residents.models import ChatSession


def touch_chat_session_activity(session: ChatSession, *, save: bool = True) -> None:
    """
    Marca atividade recente na sessão e libera novo aviso de inatividade no futuro.
    Deve ser chamado a cada mensagem inbound ou outbound relevante.
    """
    now = timezone.now()
    session.last_activity_at = now
    session.inactivity_notified = False
    if save:
        session.save(
            update_fields=["last_activity_at", "inactivity_notified", "updated_at"],
        )

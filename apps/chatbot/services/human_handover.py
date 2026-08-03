"""Human Handover: pausa/reativa o bot e timeout lazy de 2 horas."""

from __future__ import annotations

from datetime import timedelta

from django.utils import timezone

from apps.residents.models import ChatSession

HUMAN_HANDOVER_TIMEOUT = timedelta(hours=2)

# Bot pausado + estes estados = sessão inconsistente (ex.: demo/LP). Reativa em vez de mutar.
_STUCK_PAUSE_STATES = frozenset(
    {
        ChatSession.State.PRODUCT_SEARCH,
        ChatSession.State.QUANTITY_SELECTION,
        ChatSession.State.CART_REVIEW,
        ChatSession.State.AWAITING_PHOTO,
        ChatSession.State.AWAITING_MAIN_MENU,
        ChatSession.State.AWAITING_SUPPORT_DETAILS,
        ChatSession.State.SEARCHING_UNREGISTERED_PRODUCT,
        ChatSession.State.AWAITING_PRODUCT_SUGGESTION,
        ChatSession.State.AWAITING_NAME,
        ChatSession.State.AWAITING_CONDO,
    },
)


def pause_bot(session: ChatSession) -> ChatSession:
    """Pausa o bot e registra interação humana."""
    now = timezone.now()
    session.is_bot_active = False
    session.last_human_interaction_at = now
    session.save(
        update_fields=["is_bot_active", "last_human_interaction_at", "updated_at"],
    )
    return session


def resume_bot(session: ChatSession) -> ChatSession:
    """Reativa o bot (atendimento humano encerrado)."""
    session.is_bot_active = True
    session.save(update_fields=["is_bot_active", "updated_at"])
    return session


def toggle_bot(session: ChatSession, *, is_bot_active: bool) -> ChatSession:
    """Ativa ou desativa o bot manualmente."""
    if is_bot_active:
        return resume_bot(session)
    return pause_bot(session)


def ensure_bot_active_or_timeout(session: ChatSession) -> bool:
    """
    Retorna True se o bot deve processar a mensagem.

    Se o bot estiver pausado e o timeout de 2h tiver expirado (ou não houver
    last_human_interaction_at), reativa o bot e retorna True.
    Se ainda estiver em atendimento humano, retorna False.
    """
    if session.is_bot_active:
        return True

    last_at = session.last_human_interaction_at
    if last_at is None or (timezone.now() - last_at) > HUMAN_HANDOVER_TIMEOUT:
        resume_bot(session)
        return True

    return False


def should_mute_for_human(session: ChatSession) -> bool:
    """
    Estado bloqueante: fila humana ou bot pausado pelo atendente (IDLE).
    Se o bot estiver pausado mas a FSM ainda estiver em fluxo ativo, reativa
    (estado inconsistente — comum em sessões demo/localStorage).
    """
    if session.state == ChatSession.State.WAITING_FOR_HUMAN:
        return True
    if session.is_bot_active:
        return False
    if session.state in _STUCK_PAUSE_STATES:
        resume_bot(session)
        return False
    return True

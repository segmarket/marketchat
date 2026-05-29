from __future__ import annotations

from typing import Any

from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Count, QuerySet

from apps.support.models import SupportTicket, SupportTicketMessage
from apps.tenants.models import Tenant

User = get_user_model()


class SupportTicketCreateError(Exception):
    """Erro de negócio ao criar ticket."""


class SupportTicketReplyError(Exception):
    """Erro ao responder ticket."""


class SupportTicketUpdateError(Exception):
    """Erro ao atualizar status do ticket."""


def tenant_tickets_queryset(tenant_id: int) -> QuerySet[SupportTicket]:
    return (
        SupportTicket.objects.filter(tenant_id=tenant_id)
        .select_related("user")
        .annotate(message_count=Count("messages"))
        .order_by("-created_at")
    )


def get_ticket_for_tenant(*, tenant_id: int, ticket_id: int) -> SupportTicket | None:
    return (
        SupportTicket.objects.filter(pk=ticket_id, tenant_id=tenant_id)
        .select_related("user")
        .prefetch_related("messages__sender")
        .first()
    )


@transaction.atomic
def create_support_ticket(
    *,
    user: User,
    subject: str,
    description: str,
    category_route: str,
) -> SupportTicket:
    tenant_id = getattr(user, "tenant_id", None)
    if not tenant_id:
        raise SupportTicketCreateError("Conta sem empresa vinculada.")

    tenant = Tenant.objects.filter(pk=tenant_id).first()
    if not tenant:
        raise SupportTicketCreateError("Empresa não encontrada.")

    body = description.strip()
    ticket = SupportTicket.objects.create(
        tenant=tenant,
        user=user,
        subject=subject.strip(),
        description=body,
        category_route=category_route.strip(),
        status=SupportTicket.Status.NEW,
        priority=SupportTicket.Priority.MEDIUM,
    )
    SupportTicketMessage.objects.create(
        ticket=ticket,
        sender=user,
        is_from_admin=False,
        message=body,
    )
    return ticket


@transaction.atomic
def reply_to_ticket(
    *,
    ticket: SupportTicket,
    user: User,
    message: str,
) -> SupportTicketMessage:
    if ticket.status in (SupportTicket.Status.CLOSED, SupportTicket.Status.RESOLVED):
        raise SupportTicketReplyError(
            "Este chamado está encerrado e não aceita novas respostas."
        )

    text = message.strip()
    if not text:
        raise SupportTicketReplyError("Mensagem vazia.")

    return SupportTicketMessage.objects.create(
        ticket=ticket,
        sender=user,
        is_from_admin=False,
        message=text,
    )


PANEL_ALLOWED_STATUSES = frozenset(
    {
        SupportTicket.Status.RESOLVED,
        SupportTicket.Status.CLOSED,
    }
)


def update_ticket_status(*, ticket: SupportTicket, status: str) -> SupportTicket:
    if status not in PANEL_ALLOWED_STATUSES:
        raise SupportTicketUpdateError("Status inválido para esta ação.")

    if ticket.status == status:
        return ticket

    ticket.status = status
    ticket.save(update_fields=["status", "updated_at"])
    return ticket


def ticket_to_response_payload(ticket: SupportTicket) -> dict[str, Any]:
    return {
        "id": ticket.pk,
        "subject": ticket.subject,
        "status": ticket.status,
        "priority": ticket.priority,
        "created_at": ticket.created_at.isoformat(),
    }

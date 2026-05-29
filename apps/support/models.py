from __future__ import annotations

from django.conf import settings
from django.db import models

from apps.tenants.models import TenantAwareModel


class SupportTicket(TenantAwareModel):
    """Chamado manual aberto pelo operador via Suporte Copilot."""

    class Status(models.TextChoices):
        NEW = "NEW", "Novo"
        IN_PROGRESS = "IN_PROGRESS", "Em andamento"
        RESOLVED = "RESOLVED", "Resolvido"
        CLOSED = "CLOSED", "Fechado"

    class Priority(models.TextChoices):
        LOW = "LOW", "Baixa"
        MEDIUM = "MEDIUM", "Média"
        HIGH = "HIGH", "Alta"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="support_tickets",
    )
    subject = models.CharField(max_length=200)
    description = models.TextField()
    category_route = models.CharField(max_length=512)
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.NEW,
        db_index=True,
    )
    priority = models.CharField(
        max_length=16,
        choices=Priority.choices,
        default=Priority.MEDIUM,
        db_index=True,
    )

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["tenant", "status", "-created_at"]),
        ]

    def __str__(self) -> str:
        return f"#{self.pk} {self.subject[:60]}"


class SupportTicketMessage(models.Model):
    """Mensagem na thread do chamado (operador ou suporte via Admin)."""

    ticket = models.ForeignKey(
        SupportTicket,
        on_delete=models.CASCADE,
        related_name="messages",
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="support_ticket_messages",
    )
    is_from_admin = models.BooleanField(default=False)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["ticket", "created_at"]),
        ]

    def __str__(self) -> str:
        role = "Suporte" if self.is_from_admin else "Operador"
        return f"{role} em #{self.ticket_id} ({self.created_at:%d/%m/%Y %H:%M})"

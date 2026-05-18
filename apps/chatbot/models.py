from django.db import models
from django.db.models import Q

from apps.tenants.models import TenantAwareModel


class ChatbotWorkflow(TenantAwareModel):
    """Fluxo visual do chatbot WhatsApp (React Flow JSON por tenant)."""

    name = models.CharField(max_length=255, default="Fluxo principal")
    is_active = models.BooleanField(default=True)
    is_system = models.BooleanField(default=False, db_index=True)
    system_key = models.CharField(max_length=64, blank=True, default="")
    flow_data = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-updated_at"]
        indexes = [
            models.Index(fields=["tenant", "is_active"]),
            models.Index(fields=["tenant", "is_system"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "system_key"],
                condition=Q(system_key__gt=""),
                name="uniq_tenant_system_workflow_key",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.name} (tenant={self.tenant_id})"


class ChatMessageLog(TenantAwareModel):
    """Log de mensagens WhatsApp para central de atendimento."""

    class Direction(models.TextChoices):
        INBOUND = "INBOUND", "Morador"
        OUTBOUND = "OUTBOUND", "Bot"

    class IntentType(models.TextChoices):
        PURCHASE = "PURCHASE", "Compra"
        MAINTENANCE_ISSUE = "MAINTENANCE_ISSUE", "Manutenção"
        COMPLAINT = "COMPLAINT", "Reclamação"
        PAYMENT_ERROR = "PAYMENT_ERROR", "Erro de pagamento"
        STOCK_ISSUE = "STOCK_ISSUE", "Falta de estoque"
        GENERAL = "GENERAL", "Geral"

    class MessageKind(models.TextChoices):
        TEXT = "text", "Texto"
        IMAGE = "image", "Imagem"
        INTERACTIVE = "interactive", "Interativo"

    session = models.ForeignKey(
        "residents.ChatSession",
        on_delete=models.CASCADE,
        related_name="message_logs",
    )
    resident = models.ForeignKey(
        "residents.Resident",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="message_logs",
    )
    market = models.ForeignKey(
        "markets.Market",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="message_logs",
    )
    cart = models.ForeignKey(
        "sales.Cart",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="message_logs",
    )
    message_text = models.TextField(blank=True, default="")
    direction = models.CharField(max_length=16, choices=Direction.choices)
    intent_type = models.CharField(
        max_length=32,
        choices=IntentType.choices,
        blank=True,
        default="",
    )
    message_kind = models.CharField(
        max_length=16,
        choices=MessageKind.choices,
        default=MessageKind.TEXT,
    )
    attachment = models.ImageField(
        upload_to="chat_logs/%Y/%m/",
        blank=True,
        default="",
    )
    evolution_message_id = models.CharField(max_length=128, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["tenant", "-created_at"]),
            models.Index(fields=["tenant", "market", "-created_at"]),
            models.Index(fields=["tenant", "intent_type", "-created_at"]),
            models.Index(fields=["session", "created_at"]),
        ]

    def __str__(self) -> str:
        return f"ChatMessageLog({self.session_id}, {self.direction})"

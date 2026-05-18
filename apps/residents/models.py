from django.db import models
from django.utils import timezone

from apps.tenants.models import Tenant, TenantAwareModel


class Resident(TenantAwareModel):
    """Morador cadastrado via WhatsApp, vinculado a um mercado/condomínio."""

    market = models.ForeignKey(
        "markets.Market",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="residents",
    )
    phone_number = models.CharField(max_length=32, db_index=True)
    name = models.CharField(max_length=255, blank=True, default="")
    asaas_customer_id = models.CharField(max_length=64, blank=True, default="")

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "phone_number"],
                name="uniq_resident_tenant_phone",
            ),
        ]
        indexes = [
            models.Index(fields=["tenant", "market"]),
        ]

    def __str__(self) -> str:
        return f"{self.name or self.phone_number}"


class ChatSession(models.Model):
    """Estado do fluxo de onboarding e compra via WhatsApp."""

    class State(models.TextChoices):
        AWAITING_NAME = "AWAITING_NAME", "Aguardando nome"
        AWAITING_CONDO = "AWAITING_CONDO", "Aguardando condomínio"
        ACTIVE_BOT = "ACTIVE_BOT", "Bot ativo"
        AWAITING_PRODUCT_SELECTION = (
            "AWAITING_PRODUCT_SELECTION",
            "Aguardando seleção de produto",
        )
        AWAITING_QUANTITY = "AWAITING_QUANTITY", "Aguardando quantidade"
        AWAITING_LOOP_DECISION = (
            "AWAITING_LOOP_DECISION",
            "Aguardando decisão do carrinho",
        )
        AWAITING_PHOTO = "AWAITING_PHOTO", "Aguardando foto"

    tenant = models.ForeignKey(
        Tenant,
        on_delete=models.CASCADE,
        related_name="chat_sessions",
    )
    phone_number = models.CharField(max_length=32, db_index=True)
    state = models.CharField(
        max_length=32,
        choices=State.choices,
        default=State.AWAITING_NAME,
    )
    temporary_name = models.CharField(max_length=255, blank=True, default="")
    active_cart = models.ForeignKey(
        "sales.Cart",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="chat_sessions",
    )
    pending_product = models.ForeignKey(
        "products.Product",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="pending_in_sessions",
    )
    last_activity_at = models.DateTimeField(
        default=timezone.now,
        db_index=True,
        help_text="Última mensagem recebida ou enviada nesta sessão.",
    )
    inactivity_notified = models.BooleanField(
        default=False,
        db_index=True,
        help_text="Evita envio duplicado do encerramento por inatividade.",
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "phone_number"],
                name="uniq_chat_session_tenant_phone",
            ),
        ]
        indexes = [
            models.Index(
                fields=["state", "inactivity_notified", "last_activity_at"],
                name="residents_cha_inactiv_idx",
            ),
        ]

    def __str__(self) -> str:
        return f"ChatSession({self.phone_number}, {self.state})"


class ChatMessage(models.Model):
    """Mensagem trocada na sessão WhatsApp (janela deslizante para IA)."""

    class Role(models.TextChoices):
        USER = "user", "Usuário"
        ASSISTANT = "assistant", "Assistente"

    session = models.ForeignKey(
        ChatSession,
        on_delete=models.CASCADE,
        related_name="messages",
    )
    role = models.CharField(max_length=16, choices=Role.choices)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["session", "-created_at"]),
        ]

    def __str__(self) -> str:
        return f"ChatMessage({self.session_id}, {self.role})"

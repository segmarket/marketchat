from django.db import models
from django.db.models import Q
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
    phone_number = models.CharField(max_length=64, db_index=True)
    name = models.CharField(max_length=255, blank=True, default="")
    asaas_customer_id = models.CharField(max_length=64, blank=True, default="")
    is_active = models.BooleanField(default=True)
    is_anonymized = models.BooleanField(default=False, db_index=True)
    anonymized_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "phone_number"],
                condition=Q(is_anonymized=False),
                name="uniq_resident_tenant_phone_active",
            ),
        ]
        indexes = [
            models.Index(fields=["tenant", "market"]),
        ]

    def anonymize_data(self) -> None:
        from apps.lgpd.services.anonymization import perform_resident_anonymization

        perform_resident_anonymization(self)

    def __str__(self) -> str:
        return f"{self.name or self.phone_number}"


class ChatSession(models.Model):
    """Estado do fluxo de onboarding e compra via WhatsApp."""

    class State(models.TextChoices):
        AWAITING_NAME = "AWAITING_NAME", "Aguardando nome"
        AWAITING_CONDO = "AWAITING_CONDO", "Aguardando condomínio"
        IDLE = "IDLE", "Conversa livre / compra"
        AWAITING_MAIN_MENU = "AWAITING_MAIN_MENU", "Menu principal"
        AWAITING_PRODUCT_SUGGESTION = (
            "AWAITING_PRODUCT_SUGGESTION",
            "Aguardando sugestão de produto",
        )
        PRODUCT_SEARCH = "PRODUCT_SEARCH", "Busca de produto"
        QUANTITY_SELECTION = "QUANTITY_SELECTION", "Seleção de quantidade"
        CART_REVIEW = "CART_REVIEW", "Revisão do carrinho"
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
    last_discussed_product = models.ForeignKey(
        "products.Product",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="discussed_in_sessions",
        help_text="Último produto citado em disponibilidade ou busca (memória de curto prazo).",
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
    is_bot_active = models.BooleanField(
        default=True,
        db_index=True,
        help_text="Se False, o chatbot não responde automaticamente (atendimento humano).",
    )
    last_human_interaction_at = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
        help_text="Horário da última mensagem ou toggle do atendente humano.",
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

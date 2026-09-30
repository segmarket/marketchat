from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.tenants.managers import TenantManager


class Tenant(models.Model):
    """Conta / empresa do cliente."""

    class SubscriptionStatus(models.TextChoices):
        TRIAL = "TRIAL", "Trial"
        ACTIVE = "ACTIVE", "Ativa"
        OVERDUE = "OVERDUE", "Em atraso"
        SUSPENDED = "SUSPENDED", "Suspensa"
        CANCELED = "CANCELED", "Cancelada"

    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=80, unique=True)
    phone = models.CharField(max_length=32, blank=True, default="")
    cpf_cnpj = models.CharField(max_length=18, blank=True, default="")
    trial_started_at = models.DateTimeField()
    trial_ends_at = models.DateTimeField()
    subscription_status = models.CharField(
        max_length=16,
        choices=SubscriptionStatus.choices,
        default=SubscriptionStatus.TRIAL,
    )
    overdue_since = models.DateTimeField(null=True, blank=True)
    billing_blocked_at = models.DateTimeField(null=True, blank=True)
    whatsapp_logout_pending_since = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Bloqueio aplicado localmente; logout Evolution ainda não confirmado.",
    )
    whatsapp_logout_attempts = models.PositiveIntegerField(default=0)
    whatsapp_logout_last_attempt_at = models.DateTimeField(null=True, blank=True)
    whatsapp_logout_last_error = models.CharField(max_length=500, blank=True, default="")
    billing_suspension_notified_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="E-mail de suspensão enviado ao admin. Anterior a billing_blocked_at = aviso pendente.",
    )
    utm_source = models.CharField(max_length=255, blank=True, default="")
    utm_medium = models.CharField(max_length=255, blank=True, default="")
    utm_campaign = models.CharField(max_length=255, blank=True, default="")
    utm_term = models.CharField(max_length=255, blank=True, default="")
    utm_content = models.CharField(max_length=255, blank=True, default="")
    gclid = models.CharField(max_length=255, blank=True, default="")
    fbclid = models.CharField(max_length=255, blank=True, default="")
    terms_accepted_at = models.DateTimeField(null=True, blank=True)
    is_bot_active_global = models.BooleanField(
        default=True,
        help_text="Chave geral: se False, o bot não responde em nenhuma conversa.",
    )
    is_whatsapp_connected = models.BooleanField(
        default=False,
        help_text="Espelho da sessão WhatsApp ativa (Evolution). False = bot offline para clientes.",
    )
    asaas_default_customer_id = models.CharField(
        max_length=64,
        blank=True,
        default="",
        help_text="Customer Asaas Consumidor Final para cobranças PIX avulsas no chat.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def block_billing_access(self) -> None:
        self.billing_blocked_at = timezone.now()
        self.save(update_fields=["billing_blocked_at", "updated_at"])

    def clear_billing_block(self) -> None:
        self.billing_blocked_at = None
        self.save(update_fields=["billing_blocked_at", "updated_at"])

    def active_markets_count(self) -> int:
        from apps.markets.models import Market

        return Market.objects.filter(tenant=self, status=Market.Status.ACTIVE).count()

    def subscription_unit_value(self) -> float:
        return float(getattr(settings, "MARKET_MONTHLY_PRICE", 59.90))

    def computed_subscription_value(self) -> float:
        """Soma dos preços dos mercados ativos (custom_price ou preço padrão)."""
        from apps.markets.models import Market

        unit = self.subscription_unit_value()
        total = 0.0
        for market in Market.objects.filter(tenant=self, status=Market.Status.ACTIVE):
            if market.custom_price is not None:
                total += float(market.custom_price)
            else:
                total += unit
        return round(total, 2)

    def days_overdue(self) -> int:
        """Apenas exibição (dias corridos no fuso local); a carência usa billing_rules."""
        if self.overdue_since is None:
            return 0
        delta = timezone.localdate() - timezone.localdate(self.overdue_since)
        return max(0, delta.days)

    def grace_ends_at(self):
        from apps.tenants.billing_rules import grace_deadline

        if self.subscription_status != self.SubscriptionStatus.OVERDUE:
            return None
        return grace_deadline(self.overdue_since)

    def is_in_grace_period(self, *, now=None) -> bool:
        from apps.tenants.billing_rules import is_within_grace

        return self.subscription_status == self.SubscriptionStatus.OVERDUE and is_within_grace(
            self.overdue_since,
            now=now,
        )

    def ensure_billing_state(self) -> None:
        """
        Transiciona OVERDUE fora da carência para SUSPENDED (bloqueio local).
        Logout Evolution e e-mail ficam pendentes para o check_subscriptions: nada de rede na request.
        """
        from apps.tenants.billing_rules import grace_expired

        if self.subscription_status != self.SubscriptionStatus.OVERDUE:
            return
        if grace_expired(self.overdue_since):
            from apps.billing.services.tenant_suspension import suspend_tenant_for_overdue

            suspend_tenant_for_overdue(self)

    def has_messaging_access(self, *, now=None) -> bool:
        """Bot/WhatsApp: sem efeitos colaterais, mesma carência do painel e do check_subscriptions."""
        now = now or timezone.now()
        if self.subscription_status == self.SubscriptionStatus.SUSPENDED:
            return False
        if self.billing_blocked_at is not None:
            return False
        if self.subscription_status in (
            self.SubscriptionStatus.TRIAL,
            self.SubscriptionStatus.CANCELED,
        ):
            return now < self.trial_ends_at
        if self.subscription_status == self.SubscriptionStatus.OVERDUE:
            return self.is_in_grace_period(now=now)
        return True

    def has_panel_access(self) -> bool:
        self.ensure_billing_state()
        self.refresh_from_db(fields=["subscription_status", "billing_blocked_at", "overdue_since"])

        if self.subscription_status == self.SubscriptionStatus.SUSPENDED:
            return False
        if self.billing_blocked_at is not None:
            return False
        if self.subscription_status == self.SubscriptionStatus.OVERDUE:
            return self.is_in_grace_period()
        if timezone.now() < self.trial_ends_at:
            return True
        from apps.billing.models import Subscription

        try:
            sub = self.subscription
        except Subscription.DoesNotExist:
            return False
        return sub.status == Subscription.Status.ACTIVE

    def has_billing_access(self) -> bool:
        return self.has_panel_access()

    def days_left_in_trial(self) -> int:
        if timezone.now() >= self.trial_ends_at:
            return 0
        return max(0, (self.trial_ends_at.date() - timezone.now().date()).days)

    def is_trial_period_over(self) -> bool:
        return timezone.now() >= self.trial_ends_at

    def __str__(self) -> str:
        return self.name


class TenantAwareModel(models.Model):
    """Herde deste modelo para dados escopados por tenant."""

    tenant = models.ForeignKey(
        Tenant,
        on_delete=models.CASCADE,
        related_name="%(class)ss",
        db_index=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = TenantManager()
    all_objects = models.Manager()

    class Meta:
        abstract = True


class DemoNote(TenantAwareModel):
    """Recurso de exemplo para testes de isolamento entre tenants."""

    title = models.CharField(max_length=200)

    class Meta:
        ordering = ["-created_at"]

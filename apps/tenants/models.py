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
    utm_source = models.CharField(max_length=255, blank=True, default="")
    utm_medium = models.CharField(max_length=255, blank=True, default="")
    utm_campaign = models.CharField(max_length=255, blank=True, default="")
    utm_term = models.CharField(max_length=255, blank=True, default="")
    utm_content = models.CharField(max_length=255, blank=True, default="")
    gclid = models.CharField(max_length=255, blank=True, default="")
    fbclid = models.CharField(max_length=255, blank=True, default="")
    terms_accepted_at = models.DateTimeField(null=True, blank=True)
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
        if self.overdue_since is None:
            return 0
        delta = timezone.now().date() - self.overdue_since.date()
        return max(0, delta.days)

    def is_in_grace_period(self) -> bool:
        grace_days = int(getattr(settings, "BILLING_GRACE_DAYS", 3))
        return (
            self.subscription_status == self.SubscriptionStatus.OVERDUE
            and self.overdue_since is not None
            and self.days_overdue() <= grace_days
        )

    def ensure_billing_state(self) -> None:
        """Transiciona OVERDUE fora da carência para SUSPENDED."""
        if self.subscription_status != self.SubscriptionStatus.OVERDUE:
            return
        if self.overdue_since is None:
            return
        grace_days = int(getattr(settings, "BILLING_GRACE_DAYS", 3))
        if self.days_overdue() > grace_days:
            from apps.billing.services.tenant_suspension import suspend_tenant_for_overdue

            suspend_tenant_for_overdue(self)

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

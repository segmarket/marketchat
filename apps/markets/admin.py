"""
Admin de mercados.

Grupo \"Vendedores\": atribua is_staff=True e o grupo criado pela migration
`markets.0003_sellers_group` (add/change/view Market + view Tenant).
"""

from django.contrib import admin, messages
from django.db import transaction

from apps.billing.services.subscription_sync import update_tenant_subscription_value
from apps.markets.models import Market
from apps.tenants.models import Tenant


def _schedule_subscription_sync(tenant_id: int) -> None:
    def _sync() -> None:
        tenant = Tenant.objects.filter(pk=tenant_id).first()
        if tenant:
            update_tenant_subscription_value(tenant)

    transaction.on_commit(_sync)


@admin.register(Market)
class MarketAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "tenant", "status", "custom_price", "created_at")
    list_filter = ("status",)
    search_fields = ("name", "address", "tenant__name", "tenant__slug")
    autocomplete_fields = ("tenant",)
    fieldsets = (
        (
            None,
            {
                "fields": ("tenant", "name", "address", "status"),
                "description": (
                    "Selecione o cliente (tenant), preencha os dados do mercado "
                    "e, se houver negociação, informe o preço promocional."
                ),
            },
        ),
        (
            "Preço negociado",
            {
                "fields": ("custom_price",),
                "description": (
                    "Deixe em branco para usar o preço padrão do plano "
                    "(MARKET_MONTHLY_PRICE). Ao salvar, a assinatura Asaas "
                    "do cliente é recalculada automaticamente."
                ),
            },
        ),
    )

    def get_queryset(self, request):
        # Admin sem tenant no contexto: evita filtro acidental do TenantManager.
        return Market.all_objects.select_related("tenant")

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        _schedule_subscription_sync(obj.tenant_id)
        messages.info(
            request,
            "Mercado salvo. A assinatura Asaas do cliente será sincronizada em seguida.",
        )

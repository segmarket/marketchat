from __future__ import annotations

import logging

from apps.billing.models import Subscription
from apps.billing.services.asaas_client import AsaasAPIError, AsaasClient
from apps.tenants.models import Tenant

logger = logging.getLogger(__name__)


def update_tenant_subscription_value(
    tenant: Tenant,
    *,
    client: AsaasClient | None = None,
) -> None:
    """
    Sincroniza o valor da assinatura Asaas com a soma dos preços dos mercados ativos
    (custom_price por mercado ou MARKET_MONTHLY_PRICE).
    Sem mercados ativos: pausa assinatura (INACTIVE).
    """
    try:
        subscription = tenant.subscription
    except Subscription.DoesNotExist:
        logger.info(
            "update_tenant_subscription_value: tenant %s sem assinatura local",
            tenant.pk,
        )
        return

    client = client or AsaasClient()
    count = tenant.active_markets_count()
    subscription_id = subscription.asaas_subscription_id

    try:
        if count == 0:
            client.update_subscription(subscription_id, {"status": "INACTIVE"})
            logger.info(
                "Assinatura pausada (sem mercados ativos): tenant=%s sub=%s",
                tenant.pk,
                subscription_id,
            )
            return

        value = tenant.computed_subscription_value()
        client.update_subscription(
            subscription_id,
            {
                "value": value,
                "status": "ACTIVE",
                "updatePendingPayments": True,
            },
        )
        logger.info(
            "Assinatura atualizada: tenant=%s mercados=%s value=%.2f",
            tenant.pk,
            count,
            value,
        )
    except AsaasAPIError as exc:
        logger.warning(
            "Falha ao sincronizar assinatura tenant=%s: %s",
            tenant.pk,
            exc.payload or exc,
        )

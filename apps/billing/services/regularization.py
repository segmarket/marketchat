"""
Regularização de inadimplência com cartão: paga a(s) cobrança(s) exigida(s) no Asaas.

Trocar o cartão da assinatura (PUT /subscriptions/{id}/creditCard) não cobra nada; por
isso o acesso só volta quando POST /payments/{id}/payWithCreditCard confirma a cobrança
exigida (ou quando o webhook dessa mesma cobrança chegar).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Mapping

from django.core.cache import cache
from django.db import transaction

from apps.billing.models import Subscription, SubscriptionCharge
from apps.billing.services.asaas_client import AsaasAPIError, AsaasClient
from apps.billing.services.billing_history import invalidate_billing_history_cache
from apps.billing.services.payment_method import (
    _subscription_for_tenant,
    attach_card_to_subscription,
)
from apps.billing.services.subscription_charges import (
    PAID_STATUSES,
    PAYABLE_STATUSES,
    activate_tenant,
    mark_charge_paid,
    outstanding_charges,
    payment_status_of,
    sync_overdue_charges_from_asaas,
    upsert_charge,
)
from apps.tenants.models import Tenant

logger = logging.getLogger(__name__)

REGULARIZABLE_STATUSES = frozenset(
    {Tenant.SubscriptionStatus.OVERDUE, Tenant.SubscriptionStatus.SUSPENDED},
)
_LOCK_TIMEOUT_SECONDS = 180
# 402 é reservado ao bloqueio do middleware (o front redireciona ao recebê-lo).
CARD_ERROR_HTTP_STATUS = 422


def tenant_can_regularize(tenant: Tenant) -> bool:
    """Inadimplente, suspenso ou em trial vencido ainda não suspenso pelo check_subscriptions."""
    if tenant.subscription_status in REGULARIZABLE_STATUSES:
        return True
    return (
        tenant.subscription_status == Tenant.SubscriptionStatus.TRIAL
        and tenant.is_trial_period_over()
    )


class RegularizationError(Exception):
    def __init__(self, code: str, detail: str, http_status: int) -> None:
        super().__init__(detail)
        self.code = code
        self.detail = detail
        self.http_status = http_status


@dataclass
class RegularizationResult:
    status: str
    paid_charges: list[str] = field(default_factory=list)
    pending_charges: list[str] = field(default_factory=list)


def _asaas_error_detail(exc: AsaasAPIError, default: str) -> str:
    payload = exc.payload
    if isinstance(payload, dict):
        errors = payload.get("errors")
        if isinstance(errors, list) and errors and isinstance(errors[0], dict):
            return str(errors[0].get("description") or default)
    return default


def resolve_required_charges(
    tenant: Tenant,
    sub: Subscription,
    *,
    client: AsaasClient,
) -> list[SubscriptionCharge]:
    charges = list(outstanding_charges(sub))
    if charges:
        return charges
    remote = sync_overdue_charges_from_asaas(
        sub,
        client=client,
        include_pending_due=tenant.overdue_since is None,
    )
    if remote is None:
        raise RegularizationError(
            "gateway_unavailable",
            "Não foi possível consultar suas cobranças agora. Tente novamente em alguns minutos.",
            502,
        )
    return remote


def _pay_charge(
    sub: Subscription,
    charge: SubscriptionCharge,
    *,
    token: str,
    client: AsaasClient,
) -> str:
    """Retorna o status final conhecido da cobrança."""
    payment_id = charge.asaas_payment_id
    current = client.get_payment(payment_id)
    status = payment_status_of(current)
    if status in PAID_STATUSES:
        return status
    if status and status not in PAYABLE_STATUSES:
        raise RegularizationError(
            "charge_not_payable",
            "A fatura em aberto não pode mais ser paga pelo cartão "
            f"(situação {status}). Fale com o suporte para regularizar.",
            409,
        )

    try:
        result = client.pay_with_credit_card(payment_id, {"creditCardToken": token})
    except AsaasAPIError as exc:
        if exc.status_code is None:
            # Timeout/rede: consultar antes de qualquer nova tentativa (orientação Asaas).
            try:
                after = payment_status_of(client.get_payment(payment_id))
            except AsaasAPIError:
                after = ""
            if after in PAID_STATUSES:
                return after
            raise RegularizationError(
                "uncertain_result",
                "Não recebemos a confirmação do pagamento. Não tente novamente agora: "
                "se a cobrança for aprovada, o acesso é liberado automaticamente.",
                502,
            ) from exc
        raise RegularizationError(
            "card_refused",
            _asaas_error_detail(exc, "O pagamento com este cartão foi recusado."),
            CARD_ERROR_HTTP_STATUS,
        ) from exc

    with transaction.atomic():
        upsert_charge(sub, {**result, "id": payment_id}, event="PAY_WITH_CREDIT_CARD")
    return payment_status_of(result)


def regularize_with_credit_card(
    tenant: Tenant,
    credit_card: Mapping[str, Any],
    credit_card_holder_info: Mapping[str, Any],
    remote_ip: str,
    *,
    client: AsaasClient | None = None,
) -> RegularizationResult:
    if not tenant_can_regularize(tenant):
        raise RegularizationError(
            "nothing_to_regularize",
            "Não há pendência financeira a regularizar nesta conta.",
            409,
        )

    lock_key = f"billing:regularize:{tenant.pk}"
    try:
        acquired = cache.add(lock_key, "1", timeout=_LOCK_TIMEOUT_SECONDS)
    except Exception:
        # Sem cache, a consulta da cobrança antes do pagamento ainda evita cobrança dupla.
        logger.warning("Regularização sem lock (cache indisponível) tenant_id=%s", tenant.pk)
        acquired = True
    if not acquired:
        raise RegularizationError(
            "in_progress",
            "Já existe um pagamento em processamento. Aguarde alguns instantes.",
            409,
        )

    try:
        sub = _subscription_for_tenant(tenant)
        client = client or AsaasClient()

        with transaction.atomic():
            charges = resolve_required_charges(tenant, sub, client=client)
        if not charges:
            raise RegularizationError(
                "no_required_charge",
                "Não localizamos a fatura em aberto desta assinatura. "
                "Fale com o suporte para regularizar o acesso.",
                409,
            )

        try:
            token = attach_card_to_subscription(
                sub,
                credit_card,
                credit_card_holder_info,
                remote_ip,
                client=client,
            )
        except AsaasAPIError as exc:
            if exc.status_code is None:
                raise RegularizationError(
                    "gateway_unavailable",
                    "Serviço de pagamentos indisponível. Nada foi cobrado; tente novamente em instantes.",
                    502,
                ) from exc
            raise RegularizationError(
                "card_invalid",
                _asaas_error_detail(exc, "Não foi possível validar este cartão."),
                CARD_ERROR_HTTP_STATUS,
            ) from exc

        result = RegularizationResult(status="pending_confirmation")
        for charge in charges:
            status = _pay_charge(sub, charge, token=token, client=client)
            if status in PAID_STATUSES:
                with transaction.atomic():
                    locked = SubscriptionCharge.objects.select_for_update().get(pk=charge.pk)
                    mark_charge_paid(locked)
                result.paid_charges.append(charge.asaas_payment_id)
            else:
                result.pending_charges.append(charge.asaas_payment_id)
                break

        with transaction.atomic():
            locked_tenant = Tenant.objects.select_for_update().get(pk=tenant.pk)
            locked_sub = Subscription.objects.select_for_update().get(pk=sub.pk)
            if (
                not result.pending_charges
                and tenant_can_regularize(locked_tenant)
                and not outstanding_charges(locked_sub).exists()
            ):
                activate_tenant(locked_tenant, locked_sub, reason="card_regularization")
                result.status = "regularized"

        invalidate_billing_history_cache(tenant.pk)
        logger.info(
            "Regularização com cartão tenant_id=%s status=%s pagas=%s pendentes=%s",
            tenant.pk,
            result.status,
            result.paid_charges,
            result.pending_charges,
        )
        return result
    finally:
        try:
            cache.delete(lock_key)
        except Exception:
            logger.warning("Falha ao liberar lock de regularização tenant_id=%s", tenant.pk)

from __future__ import annotations

import logging
import uuid
from datetime import timedelta
from typing import Any

from django.conf import settings
from django.contrib.auth.password_validation import validate_password
from django.db import IntegrityError, transaction
from django.utils import timezone
from django.utils.text import slugify

from apps.accounts.models import User
from apps.billing.services.asaas_client import AsaasAPIError
from apps.billing.services.subscription_flow import create_trial_subscription
from apps.tenants.models import Tenant

logger = logging.getLogger(__name__)


class RegistrationError(Exception):
    """Erro de negócio ou integração durante o cadastro."""


def _unique_slug(base_slug: str) -> str:
    candidate = base_slug[:80] or "empresa"
    while Tenant.objects.filter(slug=candidate).exists():
        candidate = f"{base_slug[:60]}-{uuid.uuid4().hex[:8]}"[:80]
    return candidate


def _attribution_kwargs(attribution: dict[str, Any] | None) -> dict[str, str]:
    if not attribution:
        return {}
    fields = (
        "utm_source",
        "utm_medium",
        "utm_campaign",
        "utm_term",
        "utm_content",
        "gclid",
        "fbclid",
    )
    result: dict[str, str] = {}
    for field in fields:
        raw = attribution.get(field)
        if raw is None:
            continue
        value = str(raw).strip()[:255]
        if value:
            result[field] = value
    return result


def register_tenant_with_admin(
    *,
    company_name: str,
    slug: str | None,
    admin_email: str,
    admin_password: str,
    first_name: str,
    last_name: str,
    credit_card: dict[str, Any],
    credit_card_holder_info: dict[str, Any],
    remote_ip: str,
    attribution: dict[str, Any] | None = None,
) -> tuple[Tenant, User]:
    base = slugify(slug or company_name) or "empresa"
    now = timezone.now()
    trial_end = now + timedelta(days=settings.TRIAL_DAYS)
    final_slug = _unique_slug(base)

    prospective = User(email=admin_email)
    validate_password(admin_password, prospective)

    with transaction.atomic():
        try:
            tenant = Tenant.objects.create(
                name=company_name,
                slug=final_slug,
                trial_started_at=now,
                trial_ends_at=trial_end,
                subscription_status=Tenant.SubscriptionStatus.TRIAL,
                terms_accepted_at=now,
                **_attribution_kwargs(attribution),
            )
            user = User.objects.create_user(
                admin_email,
                password=admin_password,
                tenant=tenant,
                is_tenant_admin=True,
                first_name=first_name,
                last_name=last_name,
            )
        except IntegrityError as exc:
            raise RegistrationError("E-mail ou identificador da empresa já está em uso.") from exc
        try:
            create_trial_subscription(
                tenant,
                user,
                credit_card,
                credit_card_holder_info,
                remote_ip,
            )
        except AsaasAPIError as exc:
            if exc.status_code == 401:
                logger.warning("Asaas 401 no cadastro (sem dados de cartão no log)")
            else:
                logger.exception("Falha Asaas no cadastro")
            if "ASAAS_API_KEY" in str(exc) and "não está definida" in str(exc):
                raise RegistrationError(str(exc)) from exc
            if exc.status_code == 401:
                raise RegistrationError(
                    "Asaas recusou a autenticação (401): chave de API ausente ou inválida. "
                    "Defina ASAAS_API_KEY no .env na raiz do repositório (mesmo nível que manage.py). "
                    "A chave do sandbox costuma começar com $aact_hmlg_ (o $ faz parte do token)."
                ) from exc
            if exc.status_code == 403:
                raise RegistrationError(
                    "O Asaas não liberou tokenização de cartão na conta de produção (403). "
                    "No sandbox isso já vem habilitado; em produção é preciso solicitar ao gerente de contas "
                    "a habilitação de tokenização / cobrança por cartão na API. "
                    "Confira também ASAAS_API_URL=https://api.asaas.com/v3 e chave de produção ($aact_prod_...)."
                ) from exc
            raise RegistrationError(
                f"Não foi possível concluir o cadastro no provedor de pagamentos: {exc}"
            ) from exc
        except ValueError as exc:
            logger.exception("Falha Asaas no cadastro")
            raise RegistrationError("Não foi possível concluir o cadastro no provedor de pagamentos.") from exc

    return tenant, user

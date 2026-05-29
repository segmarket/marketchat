from __future__ import annotations

import logging
from datetime import date
from email.mime.image import MIMEImage
from pathlib import Path
from typing import Any

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import EmailMultiAlternatives
from django.template import TemplateDoesNotExist
from django.template.loader import render_to_string
from django.utils.encoding import force_bytes
from django.utils.html import strip_tags
from django.utils.http import urlsafe_base64_encode

from apps.core.constants import (
    ADDRESS_LINES,
    CNPJ,
    COMPANY_LEGAL_NAME,
    SUPPORT_EMAIL,
    SUPPORT_PHONE,
    SUPPORT_WHATSAPP_URL,
)
from apps.tenants.models import Tenant

logger = logging.getLogger(__name__)
User = get_user_model()

WELCOME_SUBJECT = "Bem-vindo ao MarketChat - Seu gerente virtual esta pronto"
PASSWORD_RESET_SUBJECT = "Recuperacao de Senha - MarketChat"
SUBSCRIPTION_SUSPENDED_SUBJECT = "MarketChat pausado - Regularize sua assinatura"


def _display_first_name(user: User) -> str:
    name = (user.first_name or "").strip()
    if name:
        return name
    local = (user.email or "").split("@")[0].strip()
    return local or "Cliente"


def _logo_path() -> Path:
    return Path(settings.EMAIL_BRAND_LOGO_PATH)


def _prepare_logo_context(context: dict[str, Any]) -> tuple[dict[str, Any], bool]:
    """Usa CID (anexo inline) quando o arquivo do logo existe — funciona no Gmail sem URL pública."""
    logo_file = _logo_path()
    if logo_file.is_file():
        merged = {**context, "logo_url": f"cid:{settings.EMAIL_BRAND_LOGO_CID}"}
        return merged, True
    return context, False


def _attach_inline_logo(msg: EmailMultiAlternatives) -> None:
    logo_file = _logo_path()
    if not logo_file.is_file():
        return
    mime = MIMEImage(logo_file.read_bytes())
    mime.add_header("Content-ID", f"<{settings.EMAIL_BRAND_LOGO_CID}>")
    mime.add_header("Content-Disposition", "inline", filename=logo_file.name)
    msg.attach(mime)


def build_email_context(**extra: Any) -> dict[str, Any]:
    context = {
        "company_legal_name": COMPANY_LEGAL_NAME,
        "cnpj": CNPJ,
        "support_email": SUPPORT_EMAIL,
        "support_phone": SUPPORT_PHONE,
        "support_whatsapp_url": SUPPORT_WHATSAPP_URL,
        "address_lines": ADDRESS_LINES,
        "logo_url": settings.EMAIL_BRAND_LOGO_URL,
        "trial_days": settings.TRIAL_DAYS,
        "current_year": date.today().year,
    }
    context.update(extra)
    return context


def send_market_transactional_email(
    subject: str,
    template_name: str,
    context: dict[str, Any],
    to_email: str,
    *,
    fail_silently: bool = False,
) -> int:
    """
    Envia e-mail transacional com versão texto puro e HTML (anti-spam).
    Retorna 1 se enviado, 0 se fail_silently e falhou.
    """
    html_template = f"emails/{template_name}.html"
    txt_template = f"emails/{template_name}.txt"

    render_context, use_cid_logo = _prepare_logo_context(context)
    html_content = render_to_string(html_template, render_context)
    try:
        text_content = render_to_string(txt_template, context)
    except TemplateDoesNotExist:
        text_content = strip_tags(html_content)

    from_email = settings.TRANSACTIONAL_FROM_EMAIL

    msg = EmailMultiAlternatives(
        subject=subject,
        body=text_content,
        from_email=from_email,
        to=[to_email],
    )
    msg.attach_alternative(html_content, "text/html")
    if use_cid_logo:
        _attach_inline_logo(msg)

    try:
        return msg.send(fail_silently=fail_silently)
    except Exception:
        if fail_silently:
            logger.exception("Falha ao enviar e-mail transacional para %s", to_email)
            return 0
        raise


def send_password_reset_email(user: User) -> None:
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    base = (settings.FRONTEND_PASSWORD_RESET_URL or "").strip().rstrip("/")
    action_url = f"{base}?uid={uid}&token={token}"

    context = build_email_context(
        first_name=_display_first_name(user),
        action_url=action_url,
    )
    send_market_transactional_email(
        PASSWORD_RESET_SUBJECT,
        "password_reset",
        context,
        user.email,
    )


def send_password_reset_email_safe(user: User) -> None:
    """Não propaga falha de SMTP — a API de reset sempre responde mensagem genérica."""
    try:
        send_password_reset_email(user)
    except Exception:
        logger.exception("Falha ao enviar e-mail de recuperacao de senha para %s", user.email)


def send_welcome_trial_email(user: User, tenant: Tenant) -> None:
    context = build_email_context(
        first_name=_display_first_name(user),
        company_name=tenant.name,
        action_url=(settings.FRONTEND_SIGNIN_URL or "").strip(),
    )
    send_market_transactional_email(
        WELCOME_SUBJECT,
        "welcome_trial",
        context,
        user.email,
    )


def send_welcome_trial_email_safe(user: User, tenant: Tenant) -> None:
    """Não propaga falha de SMTP após cadastro concluído."""
    try:
        send_welcome_trial_email(user, tenant)
    except Exception:
        logger.exception(
            "Falha ao enviar e-mail de boas-vindas para %s (tenant=%s)",
            user.email,
            tenant.pk,
        )


def send_subscription_suspended_email(
    user: User,
    tenant: Tenant,
    *,
    reason: str,
    reason_label: str,
) -> None:
    context = build_email_context(
        first_name=_display_first_name(user),
        company_name=tenant.name,
        suspension_reason_label=reason_label,
        action_url=(settings.FRONTEND_SIGNIN_URL or "").strip(),
    )
    send_market_transactional_email(
        SUBSCRIPTION_SUSPENDED_SUBJECT,
        "subscription_suspended",
        context,
        user.email,
    )


def send_subscription_suspended_email_safe(
    user: User,
    tenant: Tenant,
    *,
    reason: str,
    reason_label: str,
) -> None:
    """Não propaga falha de SMTP na task de suspensão."""
    try:
        send_subscription_suspended_email(
            user,
            tenant,
            reason=reason,
            reason_label=reason_label,
        )
    except Exception:
        logger.exception(
            "Falha ao enviar e-mail de suspensão para %s (tenant=%s reason=%s)",
            user.email,
            tenant.pk,
            reason,
        )

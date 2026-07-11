"""Alertas de vendas para novos leads."""

from __future__ import annotations

import logging

from django.conf import settings
from django.core.mail import send_mail

from apps.accounts.models import Lead

logger = logging.getLogger(__name__)


def _format_phone_for_alert(phone: str) -> str:
    digits = (phone or "").strip()
    if digits.startswith("55") and len(digits) >= 12:
        ddd = digits[2:4]
        rest = digits[4:]
        if len(rest) == 9:
            return f"({ddd}) {rest[:5]}-{rest[5:]}"
        if len(rest) == 8:
            return f"({ddd}) {rest[:4]}-{rest[4:]}"
    return digits or "—"


def notify_sales_new_lead_f1(lead: Lead) -> None:
    """Notifica vendedora por e-mail. Falha silenciosa — não bloqueia o cadastro do lead."""
    to_email = (getattr(settings, "LEAD_SALES_ALERT_EMAIL", None) or "").strip()
    if not to_email:
        return

    phone_display = _format_phone_for_alert(lead.phone)
    body = f"Novo Lead F1: {lead.full_name} - {phone_display} - {lead.email}"
    subject = f"Novo Lead F1: {lead.full_name}"

    try:
        send_mail(
            subject=subject,
            message=body,
            from_email=settings.TRANSACTIONAL_FROM_EMAIL,
            recipient_list=[to_email],
            fail_silently=False,
        )
    except Exception:
        logger.exception("Falha ao enviar alerta de lead F1 para %s", to_email)

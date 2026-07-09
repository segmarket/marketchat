"""CRM de leads capturados no cadastro (funil F1/F2)."""

from __future__ import annotations

from django.utils import timezone

from apps.accounts.models import Lead


def normalize_lead_email(email: str) -> str:
    return (email or "").strip().lower()


def normalize_lead_phone(phone: str) -> str:
    digits = "".join(c for c in (phone or "") if c.isdigit())
    if not digits:
        return ""
    if len(digits) in (10, 11):
        digits = f"55{digits}"
    return digits


def format_company_address(
    *,
    address: str,
    address_number: str,
    complement: str = "",
    cep: str = "",
) -> str:
    parts = [address.strip(), f"nº {address_number.strip()}"]
    complement = complement.strip()
    if complement:
        parts.append(complement)
    formatted = ", ".join(parts)
    cep_digits = "".join(c for c in cep if c.isdigit())
    if cep_digits:
        formatted = f"{formatted} — CEP {cep_digits}"
    return formatted


def upsert_signup_lead_f1(*, full_name: str, email: str, phone: str) -> Lead:
    """
    Cria ou atualiza lead F1 por e-mail.
    Não rebaixa lead_type de F2 para F1 nem altera status protegido.
    """
    normalized_email = normalize_lead_email(email)
    normalized_phone = normalize_lead_phone(phone)
    if not normalized_email:
        raise ValueError("E-mail do lead é obrigatório.")

    lead, created = Lead.objects.get_or_create(
        email=normalized_email,
        defaults={
            "full_name": full_name.strip(),
            "phone": normalized_phone,
            "lead_type": Lead.LeadType.F1,
            "status": Lead.Status.NOVO,
        },
    )
    if created:
        return lead

    lead.full_name = full_name.strip()
    lead.phone = normalized_phone
    update_fields = ["full_name", "phone", "updated_at"]
    if lead.lead_type != Lead.LeadType.F2:
        lead.lead_type = Lead.LeadType.F1
        update_fields.append("lead_type")
    lead.save(update_fields=update_fields)
    return lead


def upsert_signup_lead_f2(
    *,
    email: str,
    company_name: str,
    company_address: str,
    state: str,
) -> Lead:
    """
    Atualiza lead para F2 com dados da empresa.
    Cria lead mínimo se não existir (ex.: falha de rede no F1).
    """
    normalized_email = normalize_lead_email(email)
    if not normalized_email:
        raise ValueError("E-mail do lead é obrigatório.")

    lead, created = Lead.objects.get_or_create(
        email=normalized_email,
        defaults={
            "full_name": company_name.strip() or normalized_email,
            "phone": "",
            "lead_type": Lead.LeadType.F2,
            "company_name": company_name.strip(),
            "company_address": company_address.strip(),
            "state": state.strip().upper()[:2],
            "status": Lead.Status.NOVO,
        },
    )
    if created:
        return lead

    lead.company_name = company_name.strip()
    lead.company_address = company_address.strip()
    lead.state = state.strip().upper()[:2]
    lead.lead_type = Lead.LeadType.F2
    lead.save(
        update_fields=[
            "company_name",
            "company_address",
            "state",
            "lead_type",
            "updated_at",
        ],
    )
    return lead


def upsert_signup_lead(*, full_name: str, email: str, phone: str) -> Lead:
    """Compatibilidade retroativa — delega para F1."""
    return upsert_signup_lead_f1(full_name=full_name, email=email, phone=phone)


def mark_lead_converted(email: str) -> bool:
    """Marca lead como convertido após cadastro completo. Retorna False se não existir."""
    normalized_email = normalize_lead_email(email)
    if not normalized_email:
        return False

    updated = Lead.objects.filter(email=normalized_email).exclude(
        status=Lead.Status.CONVERTIDO,
    ).update(
        status=Lead.Status.CONVERTIDO,
        converted_at=timezone.now(),
    )
    return updated > 0

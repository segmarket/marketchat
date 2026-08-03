"""Anonimização de moradores (direito ao esquecimento) preservando ledger financeiro."""

from __future__ import annotations

import hashlib
import re

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.chatbot.models import ChatMessageLog
from apps.residents.models import ChatMessage, ChatSession, Resident

REDACTED_MESSAGE = "[conteúdo removido por solicitação LGPD]"
ANONYMIZED_NAME = "Usuário Anonimizado"


class ResidentAnonymizationError(Exception):
    """Erro de negócio ao anonimizar morador."""


def normalize_phone_digits(phone: str) -> str:
    return re.sub(r"\D", "", (phone or "").strip())


def build_anonymous_phone_token(*, tenant_id: int, phone_number: str) -> str:
    """Token estável e não reversível; cabe em ChatSession/Resident.phone_number (64).

    Prefixo ``anon_`` (5) + 27 hex = 32 chars — compatível também com DBs
    que ainda tenham varchar(32) na sessão antes da migration.
    """
    salt = getattr(settings, "SECRET_KEY", "marketchat")
    digest = hashlib.sha256(f"{tenant_id}:{phone_number}:{salt}".encode("utf-8")).hexdigest()
    return f"anon_{digest[:27]}"


def _delete_file_field(file_field) -> None:
    if file_field and file_field.name:
        file_field.delete(save=False)


@transaction.atomic
def perform_resident_anonymization(resident: Resident) -> None:
    if resident.is_anonymized:
        raise ResidentAnonymizationError("Morador já foi anonimizado.")

    original_phone = resident.phone_number
    anon_phone = build_anonymous_phone_token(
        tenant_id=resident.tenant_id,
        phone_number=original_phone,
    )

    resident.phone_number = anon_phone
    resident.name = ANONYMIZED_NAME
    resident.asaas_customer_id = ""
    resident.is_active = False
    resident.is_anonymized = True
    resident.anonymized_at = timezone.now()
    resident.save(
        update_fields=[
            "phone_number",
            "name",
            "asaas_customer_id",
            "is_active",
            "is_anonymized",
            "anonymized_at",
            "updated_at",
        ]
    )

    sessions = ChatSession.objects.filter(
        tenant_id=resident.tenant_id,
        phone_number=original_phone,
    )
    for session in sessions:
        session.phone_number = anon_phone
        session.temporary_name = ""
        session.state = ChatSession.State.IDLE
        session.save(
            update_fields=["phone_number", "temporary_name", "state", "updated_at"]
        )
        ChatMessage.objects.filter(session=session).update(content=REDACTED_MESSAGE)

    logs = ChatMessageLog.objects.filter(
        tenant_id=resident.tenant_id,
        resident=resident,
    )
    for log in logs:
        _delete_file_field(log.attachment)
        log.message_text = REDACTED_MESSAGE
        log.save(update_fields=["message_text", "attachment", "updated_at"])

    orphan_logs = ChatMessageLog.objects.filter(
        tenant_id=resident.tenant_id,
        session__phone_number=anon_phone,
    ).exclude(resident=resident)
    for log in orphan_logs:
        if log.message_text and log.message_text != REDACTED_MESSAGE:
            log.message_text = REDACTED_MESSAGE
            log.save(update_fields=["message_text", "updated_at"])


def anonymize_resident_by_phone(*, tenant_id: int, phone: str) -> Resident:
    digits = normalize_phone_digits(phone)
    if not digits:
        raise ResidentAnonymizationError("Telefone inválido.")

    resident = None
    for candidate in Resident.objects.filter(
        tenant_id=tenant_id,
        is_anonymized=False,
    ).select_related("market"):
        stored = normalize_phone_digits(candidate.phone_number)
        if stored == digits or stored.endswith(digits) or digits.endswith(stored):
            resident = candidate
            break
    if resident is None:
        raise ResidentAnonymizationError("Morador não encontrado para este telefone.")

    perform_resident_anonymization(resident)
    return resident

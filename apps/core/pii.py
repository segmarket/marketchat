"""
Utilitários para mascarar PII em logs.

Nunca registre em logger números de cartão, CPF/CNPJ ou telefones completos.
Use estas funções antes de passar dados sensíveis a logger.info/warning/error.
"""

from __future__ import annotations

import re


def _digits_only(value: str) -> str:
    return re.sub(r"\D", "", value or "")


def mask_phone(value: str) -> str:
    digits = _digits_only(value)
    if len(digits) <= 4:
        return "****"
    return f"{digits[:4]}****{digits[-4:]}"


def mask_cpf(value: str) -> str:
    digits = _digits_only(value)
    if len(digits) < 4:
        return "***"
    return f"***{digits[-2:]}"


def mask_email(value: str) -> str:
    email = (value or "").strip()
    if "@" not in email:
        return "***"
    local, domain = email.split("@", 1)
    if len(local) <= 1:
        masked_local = "*"
    else:
        masked_local = f"{local[0]}***"
    return f"{masked_local}@{domain}"


def mask_jid(remote_jid: str) -> str:
    phone = remote_jid.split("@")[0].split(":")[0] if remote_jid else ""
    return mask_phone(phone)

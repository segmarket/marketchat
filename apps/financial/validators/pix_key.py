from __future__ import annotations

from django.core.validators import EmailValidator

from apps.financial.choices import PixKeyType

_EMAIL_VALIDATOR = EmailValidator(message="Formato de e-mail inválido.")


def _digits_only(value: str) -> str:
    return "".join(c for c in value if c.isdigit())


def _is_repeated_digits(digits: str) -> bool:
    return len(digits) > 0 and len(set(digits)) == 1


def _is_valid_cpf(digits: str) -> bool:
    if len(digits) != 11 or _is_repeated_digits(digits):
        return False

    total = sum(int(digits[i]) * (10 - i) for i in range(9))
    remainder = total % 11
    d1 = 0 if remainder < 2 else 11 - remainder
    if d1 != int(digits[9]):
        return False

    total = sum(int(digits[i]) * (11 - i) for i in range(10))
    remainder = total % 11
    d2 = 0 if remainder < 2 else 11 - remainder
    return d2 == int(digits[10])


def _is_valid_cnpj(digits: str) -> bool:
    if len(digits) != 14 or _is_repeated_digits(digits):
        return False

    weights1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    weights2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]

    total = sum(int(digits[i]) * weights1[i] for i in range(12))
    remainder = total % 11
    d1 = 0 if remainder < 2 else 11 - remainder
    if d1 != int(digits[12]):
        return False

    total = sum(int(digits[i]) * weights2[i] for i in range(13))
    remainder = total % 11
    d2 = 0 if remainder < 2 else 11 - remainder
    return d2 == int(digits[13])


def validate_pix_key_for_type(pix_key_type: str, raw_value: str) -> str:
    cleaned = (raw_value or "").strip()
    if not cleaned:
        raise ValueError("Informe a chave Pix.")

    if pix_key_type == PixKeyType.CPF:
        digits = _digits_only(cleaned)
        if len(digits) != 11:
            raise ValueError("Formato de CPF inválido.")
        if not _is_valid_cpf(digits):
            raise ValueError("Formato de CPF inválido.")
        return digits

    if pix_key_type == PixKeyType.CNPJ:
        digits = _digits_only(cleaned)
        if len(digits) != 14:
            raise ValueError("Formato de CNPJ inválido.")
        if not _is_valid_cnpj(digits):
            raise ValueError("Formato de CNPJ inválido.")
        return digits

    if pix_key_type == PixKeyType.PHONE:
        digits = _digits_only(cleaned)
        if len(digits) not in {10, 11}:
            raise ValueError("Formato de celular inválido.")
        return digits

    if pix_key_type == PixKeyType.EMAIL:
        normalized = cleaned.lower()
        try:
            _EMAIL_VALIDATOR(normalized)
        except Exception as exc:
            raise ValueError("Formato de e-mail inválido.") from exc
        return normalized

    if pix_key_type == PixKeyType.RANDOM:
        if len(cleaned) < 8:
            raise ValueError("Chave aleatória inválida.")
        return cleaned

    raise ValueError("Chave Pix inválida para o tipo selecionado.")


def mask_pix_key_for_display(pix_key_type: str, pix_key: str) -> str:
    if not pix_key:
        return ""

    if pix_key_type == PixKeyType.EMAIL:
        local, _, domain = pix_key.partition("@")
        if not domain:
            return "***"
        visible = local[:2] if len(local) > 2 else (local[:1] if local else "*")
        return f"{visible}***@{domain}"

    if pix_key_type == PixKeyType.RANDOM:
        if len(pix_key) <= 4:
            return "****"
        return f"****…{pix_key[-4:]}"

    digits = _digits_only(pix_key)
    if len(digits) <= 4:
        return "****"

    last4 = digits[-4:]

    if pix_key_type == PixKeyType.CPF:
        return f"***.***.{last4[:3]}-{last4[3:]}"

    if pix_key_type == PixKeyType.CNPJ:
        return f"**.***.***/{last4[:2]}{last4[2:]}-**"

    if pix_key_type == PixKeyType.PHONE:
        if len(digits) == 11:
            return f"(**) *****-{last4}"
        return f"(**) ****-{last4}"

    return f"{'*' * max(0, len(digits) - 4)}{last4}"

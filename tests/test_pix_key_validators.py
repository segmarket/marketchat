import pytest

from apps.financial.choices import PixKeyType
from apps.financial.validators.pix_key import (
    mask_pix_key_for_display,
    validate_pix_key_for_type,
)

VALID_CPF = "529.982.247-25"
VALID_CNPJ = "11.222.333/0001-81"


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (VALID_CPF, "52998224725"),
        ("52998224725", "52998224725"),
    ],
)
def test_validate_cpf_accepts_valid_values(raw, expected):
    assert validate_pix_key_for_type(PixKeyType.CPF, raw) == expected


def test_validate_cpf_rejects_invalid_checksum():
    with pytest.raises(ValueError, match="CPF"):
        validate_pix_key_for_type(PixKeyType.CPF, "111.111.111-11")


def test_validate_cpf_rejects_repeated_digits():
    with pytest.raises(ValueError, match="CPF"):
        validate_pix_key_for_type(PixKeyType.CPF, "11111111111")


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (VALID_CNPJ, "11222333000181"),
        ("11222333000181", "11222333000181"),
    ],
)
def test_validate_cnpj_accepts_valid_values(raw, expected):
    assert validate_pix_key_for_type(PixKeyType.CNPJ, raw) == expected


def test_validate_cnpj_rejects_invalid_checksum():
    with pytest.raises(ValueError, match="CNPJ"):
        validate_pix_key_for_type(PixKeyType.CNPJ, "11.111.111/1111-11")


def test_validate_phone_accepts_ten_or_eleven_digits():
    assert validate_pix_key_for_type(PixKeyType.PHONE, "(11) 3333-4444") == "1133334444"
    assert validate_pix_key_for_type(PixKeyType.PHONE, "(11) 99999-8888") == "11999998888"


def test_validate_phone_rejects_incomplete_number():
    with pytest.raises(ValueError, match="celular"):
        validate_pix_key_for_type(PixKeyType.PHONE, "(11) 9999")


def test_validate_email_normalizes_and_accepts():
    assert validate_pix_key_for_type(PixKeyType.EMAIL, "Mercado@Example.com") == "mercado@example.com"


def test_validate_email_rejects_invalid_format():
    with pytest.raises(ValueError, match="e-mail"):
        validate_pix_key_for_type(PixKeyType.EMAIL, "invalido")


def test_validate_random_requires_minimum_length():
    assert validate_pix_key_for_type(PixKeyType.RANDOM, "abcd1234") == "abcd1234"
    with pytest.raises(ValueError, match="aleatória"):
        validate_pix_key_for_type(PixKeyType.RANDOM, "abc")


def test_mask_pix_key_for_display_formats_by_type():
    assert mask_pix_key_for_display(PixKeyType.EMAIL, "mercado@example.com") == "me***@example.com"
    assert mask_pix_key_for_display(PixKeyType.CPF, "52998224725") == "***.***.472-5"
    assert mask_pix_key_for_display(PixKeyType.RANDOM, "a1b2c3d4e5f6") == "****…e5f6"

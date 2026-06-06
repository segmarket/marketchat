import pytest

from apps.financial.choices import PixKeyType
from apps.financial.services.asaas_transfers import (
    map_pix_key_type_to_asaas,
    map_transfer_status_to_withdrawal,
    mask_pix_key_for_log,
    normalize_pix_key_for_asaas,
)
from apps.financial.models import WithdrawalRequest


def test_map_pix_key_type_to_asaas():
    assert map_pix_key_type_to_asaas(PixKeyType.PHONE) == "PHONE"
    assert map_pix_key_type_to_asaas(PixKeyType.RANDOM) == "EVP"
    assert map_pix_key_type_to_asaas(PixKeyType.EMAIL) == "EMAIL"


def test_normalize_pix_key_strips_cpf_punctuation():
    assert normalize_pix_key_for_asaas(PixKeyType.CPF, "111.444.777-35") == "11144477735"


def test_normalize_pix_key_lowercases_email():
    assert normalize_pix_key_for_asaas(PixKeyType.EMAIL, "  Mercado@Example.COM ") == "mercado@example.com"


def test_mask_pix_key_for_log():
    assert "@" in mask_pix_key_for_log(PixKeyType.EMAIL, "mercado@example.com")
    assert mask_pix_key_for_log(PixKeyType.CPF, "11144477735").endswith("7735")


@pytest.mark.parametrize(
    ("asaas_status", "expected"),
    [
        ("DONE", WithdrawalRequest.Status.PAID),
        ("CONFIRMED", WithdrawalRequest.Status.PAID),
        ("PENDING", WithdrawalRequest.Status.PROCESSING),
        ("PROCESSING", WithdrawalRequest.Status.PROCESSING),
    ],
)
def test_map_transfer_status_to_withdrawal(asaas_status, expected):
    assert map_transfer_status_to_withdrawal(asaas_status) == expected

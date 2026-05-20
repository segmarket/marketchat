import pytest

from apps.sales.services.purchase_context import is_purchase_without_product
from apps.sales.services.resident_ai_context import (
    build_resident_dynamic_context,
    resident_display_name,
    resident_first_name_from_string,
)
from tests.factories import ResidentFactory


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("Joao das couve", "Joao"),
        ("  Maria  ", "Maria"),
        ("", "Morador"),
        (None, "Morador"),
        ("pedro", "Pedro"),
    ],
)
def test_resident_first_name_from_string(raw, expected):
    assert resident_first_name_from_string(raw) == expected


@pytest.mark.django_db
def test_resident_display_name_uses_first_name_only():
    resident = ResidentFactory(name="Ana Paula Silva")
    assert resident_display_name(resident) == "Ana"


@pytest.mark.django_db
def test_build_resident_dynamic_context_omits_full_name():
    resident = ResidentFactory(name="Ana Paula Silva")
    ctx = build_resident_dynamic_context(resident)
    assert "Ana" in ctx
    assert "Ana Paula" not in ctx
    assert "primeiro nome" in ctx.lower()
    assert "casual" in ctx.lower() or "gírias" in ctx.lower()
    assert "anti-abuso" in ctx.lower()


@pytest.mark.parametrize(
    "text",
    [
        "E ae, beleza? Como mando o pix?",
        "Como faço para pagar no pix?",
        "Quero fechar no pix",
    ],
)
def test_is_purchase_without_product_detects_pix_phrases(text):
    assert is_purchase_without_product(text) is True

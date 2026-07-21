from decimal import Decimal
from unittest import mock

import pytest

from apps.integrations.services.evolution_client import (
    EvolutionClient,
    _normalize_reply_buttons,
)
from apps.sales.services.whatsapp_interactive import (
    build_numbered_product_catalog,
    send_cart_decision_buttons,
    send_product_list,
)
from tests.factories import ProductFactory, TenantFactory, WhatsappInstanceFactory


def test_normalize_reply_buttons_maps_text_to_display_text():
    buttons = _normalize_reply_buttons(
        [
            {"id": "cart:add_more", "text": "Adicionar mais"},
            {"id": "cart:checkout", "text": "Finalizar"},
        ],
    )
    assert buttons == [
        {"type": "reply", "id": "cart:add_more", "displayText": "Adicionar mais"},
        {"type": "reply", "id": "cart:checkout", "displayText": "Finalizar"},
    ]


def test_send_list_uses_footer_text_not_footer():
    client = EvolutionClient(base_url="http://evo.test")
    captured: dict = {}

    def fake_request(method, path, *, apikey, body=None, timeout=30):
        captured["method"] = method
        captured["path"] = path
        captured["body"] = body
        return {"message": "success"}

    with mock.patch.object(client, "_request", side_effect=fake_request):
        client.send_list(
            instance_api_key="tok",
            number="5511999999999",
            title="Produtos",
            description="Escolha",
            button_text="Ver",
            sections=[{"title": "Cat", "rows": []}],
            footer="Rodapé",
        )

    assert captured["path"] == "/send/list"
    assert captured["body"]["footerText"] == "Rodapé"
    assert "footer" not in captured["body"]
    assert captured["body"]["values"] == captured["body"]["sections"]


def test_send_buttons_normalizes_payload():
    client = EvolutionClient(base_url="http://evo.test")
    captured: dict = {}

    def fake_request(method, path, *, apikey, body=None, timeout=30):
        captured["body"] = body
        return {"message": "success"}

    with mock.patch.object(client, "_request", side_effect=fake_request):
        client.send_buttons(
            instance_api_key="tok",
            number="5511999999999",
            title="Carrinho",
            description="Desc",
            buttons=[{"id": "a", "text": "Um"}],
        )

    assert captured["body"]["buttons"] == [
        {"type": "reply", "id": "a", "displayText": "Um"},
    ]


def test_build_numbered_product_catalog():
    products = [
        ProductFactory.build(name="Coca Cola Lata Zero 350ml", price=Decimal("6.50")),
    ]
    text = build_numbered_product_catalog(products)
    assert "1. Coca Cola Lata Zero 350ml" in text
    assert "R$ 6,50" in text
    assert "número" in text.lower()


@pytest.mark.django_db
@mock.patch("apps.sales.services.whatsapp_interactive.send_whatsapp_reply")
def test_send_product_list_uses_plain_text_only(mock_send, db):
    tenant = TenantFactory()
    instance = WhatsappInstanceFactory(tenant=tenant)
    products = [ProductFactory(tenant=tenant, name="Coca Zero", sku="COCA1")]

    send_product_list(instance, "5511999887766", products)

    mock_send.assert_called_once()
    body = mock_send.call_args[0][2]
    assert "1. Coca Zero" in body
    assert "Encontrei estes produtos" in body


@pytest.mark.django_db
@mock.patch("apps.sales.services.whatsapp_interactive.send_whatsapp_reply")
def test_send_cart_decision_uses_plain_text_only(mock_send, db):
    tenant = TenantFactory()
    instance = WhatsappInstanceFactory(tenant=tenant)

    send_cart_decision_buttons(
        instance,
        "5511999887766",
        product_name="Coca",
        quantity=2,
        subtotal=Decimal("12.00"),
    )

    mock_send.assert_called_once()
    body = mock_send.call_args[0][2]
    assert "1 — Adicionar mais" in body
    assert "2 — Finalizar" in body

from unittest import mock

import pytest

from apps.residents.models import ChatSession
from apps.sales.models import Cart
from apps.sales.services.cart_flow import process_cart_flow
from apps.sales.services.intent_gatekeeper import (
    COMPLAINT,
    PURCHASE,
    STOCK_ISSUE,
    classify_user_intent,
)
from apps.tenants.context import tenant_scope
from tests.factories import (
    CartFactory,
    ChatSessionFactory,
    ResidentFactory,
    TenantFactory,
    WhatsappInstanceFactory,
)

MAGNUM_MESSAGE = "Boa noite, queria comprar o Magnum mas esta em falta"


def test_heuristic_classifies_magnum_stock_issue_without_openai():
    assert classify_user_intent(MAGNUM_MESSAGE) == STOCK_ISSUE


def test_heuristic_classifies_complaint_without_openai():
    assert classify_user_intent("Quero fazer uma reclamação sobre o atendimento") == COMPLAINT
    assert classify_user_intent("Estou muito insatisfeito com a compra de ontem") == COMPLAINT


@pytest.mark.django_db
def test_openai_gatekeeper_prompt_includes_few_shot_examples(settings):
    settings.OPENAI_API_KEY = "test-key"
    with (
        mock.patch(
            "apps.sales.services.intent_gatekeeper._detect_stock_issue_heuristic",
            return_value=False,
        ),
        mock.patch(
            "apps.chatbot.services.chatbot_core.complete_plain",
            return_value="STOCK_ISSUE",
        ) as complete,
    ):
        tag = classify_user_intent("Queria comprar o Magnum mas está em falta")

    assert tag == STOCK_ISSUE
    kwargs = complete.call_args.kwargs
    assert kwargs.get("apply_conciseness_rule") is False
    assert "REGRA DE PRIORIDADE MÁXIMA" in kwargs["static_system"]
    assert "Magnum" in kwargs["static_system"]


@pytest.mark.django_db
def test_magnum_stock_issue_skips_purchase_flow():
    from tests.test_cart_flow import _event_text

    tenant = TenantFactory()
    instance = WhatsappInstanceFactory(tenant=tenant)
    resident = ResidentFactory(
        tenant=tenant,
        phone_number="5511999887766",
        name="Alexandre Favero",
    )
    ChatSessionFactory(
        tenant=tenant,
        phone_number=resident.phone_number,
        state=ChatSession.State.IDLE,
    )

    with (
        mock.patch(
            "apps.sales.services.active_bot_router.classify_user_intent",
            return_value=STOCK_ISSUE,
        ) as classify,
        mock.patch("apps.sales.services.cart_flow.extract_product_term") as extract,
        mock.patch("apps.sales.services.cart_flow.send_product_list") as send_list,
        mock.patch(
            "apps.sales.services.stock_issue_handler.send_whatsapp_reply",
        ) as send_reply,
        mock.patch(
            "apps.sales.services.stock_issue_handler.notify_owner_restock_issue",
        ) as notify_owner,
        mock.patch(
            "apps.sales.services.stock_issue_handler.extract_stock_product_label",
            return_value="Magnum",
        ),
    ):
        with tenant_scope(tenant.id):
            handled = process_cart_flow(
                tenant.id,
                instance,
                resident.phone_number,
                _event_text(MAGNUM_MESSAGE, resident.phone_number),
            )

    assert handled is True
    classify.assert_called_once()
    extract.assert_not_called()
    send_list.assert_not_called()
    send_reply.assert_called_once()
    body = send_reply.call_args[0][2]
    assert "Magnum" in body
    assert "em falta" in body
    notify_owner.assert_called_once()


@pytest.mark.django_db
def test_purchase_still_routes_when_no_stock_signal():
    from tests.test_cart_flow import _event_text

    tenant = TenantFactory()
    instance = WhatsappInstanceFactory(tenant=tenant)
    resident = ResidentFactory(tenant=tenant, phone_number="5511999887766")
    ChatSessionFactory(
        tenant=tenant,
        phone_number=resident.phone_number,
        state=ChatSession.State.IDLE,
    )

    with (
        mock.patch(
            "apps.sales.services.active_bot_router.classify_user_intent",
            return_value=PURCHASE,
        ),
        mock.patch(
            "apps.sales.services.cart_flow.extract_product_term",
            return_value="coca cola",
        ),
        mock.patch("apps.sales.services.cart_flow.send_product_list"),
        mock.patch("apps.sales.services.cart_flow.send_whatsapp_reply"),
    ):
        with tenant_scope(tenant.id):
            handled = process_cart_flow(
                tenant.id,
                instance,
                resident.phone_number,
                _event_text("Quero comprar uma coca cola", resident.phone_number),
            )

    assert handled is True

from decimal import Decimal
from unittest import mock

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from apps.demo.services.chat import session_id_to_demo_phone
from apps.demo.services.portal import ensure_demo_portal
from apps.integrations.services.message_media import OUT_OF_CONTEXT_IMAGE_REPLY
from apps.markets.models import Market
from apps.products.models import Product
from apps.residents.models import ChatSession, Resident
from apps.residents.services.condo_match import find_market_by_query
from apps.sales.models import Cart
from apps.tenants.context import tenant_scope


@pytest.mark.django_db
def test_ensure_demo_portal_creates_catalog():
    bundle = ensure_demo_portal()
    assert bundle.tenant.slug == "portal-demo"
    assert bundle.market.name == "Portal"
    assert bundle.instance.api_key == "demo-no-evolution"
    with tenant_scope(bundle.tenant.id):
        assert Product.objects.filter(tenant=bundle.tenant).count() >= 4
        names = set(
            Market.objects.filter(
                tenant=bundle.tenant,
                status=Market.Status.ACTIVE,
            ).values_list("name", flat=True)
        )
        assert names >= {"Portal", "Aurora"}


@pytest.mark.django_db
def test_demo_portal_finds_aurora_market():
    bundle = ensure_demo_portal()
    with tenant_scope(bundle.tenant.id):
        market = find_market_by_query(bundle.tenant.id, "Aurora")
    assert market is not None
    assert market.name == "Aurora"


@pytest.mark.django_db
def test_demo_chat_does_not_call_evolution():
    client = APIClient()
    with mock.patch(
        "apps.integrations.services.evolution_client.EvolutionClient.send_text"
    ) as send_text:
        with mock.patch(
            "apps.residents.services.onboarding_flow.analyze_onboarding_message",
            return_value=None,
        ):
            response = client.post(
                reverse("demo-chat"),
                {"message": "oi", "session_id": "11111111-1111-4111-8111-111111111111"},
                format="json",
            )

    assert response.status_code == 200
    data = response.json()
    assert data["session_id"]
    assert data["reply"]
    assert "nome" in data["reply"].lower() or "privacidade" in data["reply"].lower()
    send_text.assert_not_called()


@pytest.mark.django_db
def test_demo_chat_keeps_session_and_completes_onboarding():
    client = APIClient()
    session_id = "22222222-2222-4222-8222-222222222222"
    phone = session_id_to_demo_phone(session_id)
    bundle = ensure_demo_portal()

    from apps.residents.services.onboarding_ai import OnboardingAIResult

    first = OnboardingAIResult(
        nome="Maria",
        condominio=None,
        intencao_primaria="compra",
        acao_imediata_codigo="continuar_onboarding",
        resposta_texto="Oi Maria! Qual o nome do seu condomínio?",
    )
    second = OnboardingAIResult(
        nome=None,
        condominio="Portal",
        intencao_primaria="compra",
        acao_imediata_codigo="continuar_onboarding",
        resposta_texto="",
    )

    with mock.patch(
        "apps.integrations.services.evolution_client.EvolutionClient.send_text"
    ) as send_text:
        with mock.patch(
            "apps.residents.services.onboarding_flow.analyze_onboarding_message",
            side_effect=[first, second],
        ):
            r1 = client.post(
                reverse("demo-chat"),
                {"message": "Oi, sou a Maria", "session_id": session_id},
                format="json",
            )
            r2 = client.post(
                reverse("demo-chat"),
                {"message": "Portal", "session_id": session_id},
                format="json",
            )

    assert r1.status_code == 200
    assert r2.status_code == 200
    assert r1.json()["session_id"] == session_id
    assert r2.json()["session_id"] == session_id
    assert "cadastro" in r2.json()["reply"].lower() or "encontrei" in r2.json()["reply"].lower()
    send_text.assert_not_called()

    with tenant_scope(bundle.tenant.id):
        assert Resident.objects.filter(phone_number=phone, market=bundle.market).exists()
        session = ChatSession.objects.get(tenant=bundle.tenant, phone_number=phone)
        assert session.state in {
            ChatSession.State.AWAITING_MAIN_MENU,
            ChatSession.State.PRODUCT_SEARCH,
            ChatSession.State.IDLE,
            ChatSession.State.AWAITING_SUPPORT_DETAILS,
        }


@pytest.mark.django_db
def test_demo_chat_requires_message():
    client = APIClient()
    response = client.post(reverse("demo-chat"), {"message": "  "}, format="json")
    assert response.status_code == 400


@pytest.mark.django_db
def test_demo_chat_media_out_of_context():
    client = APIClient()
    session_id = "33333333-3333-4333-8333-333333333333"
    phone = session_id_to_demo_phone(session_id)
    bundle = ensure_demo_portal()

    with tenant_scope(bundle.tenant.id):
        Resident.objects.create(
            tenant=bundle.tenant,
            market=bundle.market,
            phone_number=phone,
            name="Demo User",
        )
        ChatSession.objects.create(
            tenant=bundle.tenant,
            phone_number=phone,
            state=ChatSession.State.IDLE,
        )

    with mock.patch(
        "apps.integrations.services.evolution_client.EvolutionClient.send_text"
    ) as send_text:
        with mock.patch(
            "apps.billing.services.asaas_pix_charge.create_cart_pix_charge"
        ) as create_pix:
            response = client.post(
                reverse("demo-chat"),
                {
                    "message": "[MEDIA:IMAGE]",
                    "is_media": True,
                    "session_id": session_id,
                },
                format="json",
            )

    assert response.status_code == 200
    reply = response.json()["reply"]
    assert OUT_OF_CONTEXT_IMAGE_REPLY in reply
    send_text.assert_not_called()
    create_pix.assert_not_called()


@pytest.mark.django_db
def test_demo_chat_media_awaiting_photo_returns_stub_pix():
    client = APIClient()
    session_id = "44444444-4444-4444-8444-444444444444"
    phone = session_id_to_demo_phone(session_id)
    bundle = ensure_demo_portal()

    with tenant_scope(bundle.tenant.id):
        resident = Resident.objects.create(
            tenant=bundle.tenant,
            market=bundle.market,
            phone_number=phone,
            name="Demo Checkout",
        )
        cart = Cart.objects.create(
            tenant=bundle.tenant,
            resident=resident,
            status=Cart.Status.AWAITING_PHOTO,
            total_value=Decimal("12.50"),
        )
        ChatSession.objects.create(
            tenant=bundle.tenant,
            phone_number=phone,
            state=ChatSession.State.AWAITING_PHOTO,
            active_cart=cart,
        )

    with mock.patch(
        "apps.integrations.services.evolution_client.EvolutionClient.send_text"
    ) as send_text:
        with mock.patch(
            "apps.billing.services.asaas_pix_charge.create_cart_pix_charge"
        ) as create_pix:
            response = client.post(
                reverse("demo-chat"),
                {"is_media": True, "session_id": session_id},
                format="json",
            )

    assert response.status_code == 200
    reply = response.json()["reply"]
    assert "copie o código Pix" in reply
    assert "DEMO-MARKETCHAT-PIX" in reply
    send_text.assert_not_called()
    create_pix.assert_not_called()

    with tenant_scope(bundle.tenant.id):
        cart.refresh_from_db()
        session = ChatSession.objects.get(tenant=bundle.tenant, phone_number=phone)
        assert cart.status == Cart.Status.AWAITING_PAYMENT
        assert session.state == ChatSession.State.IDLE
        assert cart.product_photo
        assert session.last_discussed_product_id is None
        assert session.temporary_name == ""
        assert session.pending_intent == ""
        assert session.pending_product_id is None


@pytest.mark.django_db
def test_demo_chat_openai_failure_returns_soft_fallback_reply():
    from apps.residents.services.onboarding_ai import ONBOARDING_AI_SOFT_FALLBACK_TEXT

    client = APIClient()
    session_id = "33333333-3333-4333-8333-333333333333"

    with mock.patch(
        "apps.integrations.services.evolution_client.EvolutionClient.send_text"
    ) as send_text:
        with mock.patch(
            "apps.residents.services.onboarding_ai.settings.OPENAI_API_KEY",
            "sk-test",
        ):
            with mock.patch(
                "apps.chatbot.services.chatbot_core._get_client",
                side_effect=ConnectionError("Temporary failure in name resolution"),
            ):
                response = client.post(
                    reverse("demo-chat"),
                    {"message": "oi", "session_id": session_id},
                    format="json",
                )

    assert response.status_code == 200
    data = response.json()
    assert data["session_id"] == session_id
    assert data["reply"]
    assert ONBOARDING_AI_SOFT_FALLBACK_TEXT in data["reply"]
    send_text.assert_not_called()


@pytest.mark.django_db
def test_demo_chat_turn_exception_never_returns_empty_reply():
    from apps.demo.services.chat import DEMO_EMPTY_REPLY_FALLBACK

    client = APIClient()
    session_id = "44444444-4444-4444-8444-444444444444"

    with mock.patch(
        "apps.demo.views.process_demo_chat_turn",
        side_effect=RuntimeError("boom"),
    ):
        response = client.post(
            reverse("demo-chat"),
            {"message": "oi", "session_id": session_id},
            format="json",
        )

    assert response.status_code == 200
    data = response.json()
    assert data["reply"] == DEMO_EMPTY_REPLY_FALLBACK
    assert data["session_id"] == session_id

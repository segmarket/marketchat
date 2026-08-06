from datetime import datetime
from unittest import mock
from zoneinfo import ZoneInfo

import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework_simplejwt.tokens import RefreshToken

from apps.integrations.services.webhook_parser import parse_evolution_payload
from apps.markets.models import Market
from apps.residents.models import ChatSession, Resident
from apps.residents.services.condo_match import find_market_by_query, match_markets_by_query
from apps.residents.services.greeting import greeting_for_now
from apps.residents.services.handlers.condo import (
    RETRY_CONDO_NAME_MESSAGE,
    SUGGESTED_CONDOS_KEY,
)
from apps.residents.services.onboarding_flow import (
    REJECT_CONDO_MESSAGE,
    build_onboarding_privacy_message,
    process_inbound_message,
    resident_has_completed_onboarding,
)
from apps.tenants.context import tenant_scope
from tests.factories import (
    ChatSessionFactory,
    MarketFactory,
    ResidentFactory,
    TenantFactory,
    UserFactory,
    WhatsappInstanceFactory,
)

SAO_PAULO = ZoneInfo("America/Sao_Paulo")


def _auth(client, user):
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(user).access_token}")


@pytest.mark.parametrize(
    "hour,expected",
    [
        (8, "Bom dia"),
        (14, "Boa tarde"),
        (20, "Boa noite"),
        (3, "Boa noite"),
    ],
)
def test_greeting_for_now(hour, expected):
    fixed = datetime(2026, 5, 17, hour, 0, tzinfo=SAO_PAULO)
    with mock.patch("apps.residents.services.greeting.timezone.localtime", return_value=fixed):
        assert greeting_for_now() == expected


def test_onboarding_privacy_message_contains_policy_link():
    message = build_onboarding_privacy_message()
    assert "privacidade" in message.lower()
    assert "concorda" in message.lower()


@pytest.mark.django_db
def test_onboarding_start_includes_privacy_notice():
    tenant = TenantFactory()
    instance = WhatsappInstanceFactory(tenant=tenant)
    phone = "5511999887766"

    with mock.patch("apps.residents.services.onboarding_flow.send_whatsapp_reply") as send:
        with tenant_scope(tenant.id):
            process_inbound_message(tenant.id, instance, phone, "oi")

    assert "privacidade" in send.call_args[0][2].lower()


@pytest.mark.django_db
def test_onboarding_awaiting_name_to_awaiting_condo():
    tenant = TenantFactory()
    instance = WhatsappInstanceFactory(tenant=tenant)
    session = ChatSessionFactory(
        tenant=tenant,
        phone_number="5511999887766",
        state=ChatSession.State.AWAITING_NAME,
    )

    with mock.patch("apps.residents.services.onboarding_flow.send_whatsapp_reply") as send:
        with tenant_scope(tenant.id):
            handled = process_inbound_message(
                tenant.id,
                instance,
                session.phone_number,
                "Maria Silva",
            )

    assert handled is True
    session.refresh_from_db()
    assert session.state == ChatSession.State.AWAITING_CONDO
    assert session.temporary_name == "Maria Silva"
    assert "Prazer em te conhecer" in send.call_args[0][2]


@pytest.mark.django_db
def test_onboarding_rejects_unknown_condo():
    tenant = TenantFactory()
    instance = WhatsappInstanceFactory(tenant=tenant)
    phone = "5511777666555"
    ChatSessionFactory(
        tenant=tenant,
        phone_number=phone,
        state=ChatSession.State.AWAITING_CONDO,
        temporary_name="João",
    )

    with mock.patch("apps.residents.services.onboarding_flow.send_whatsapp_reply") as send:
        with tenant_scope(tenant.id):
            process_inbound_message(tenant.id, instance, phone, "Condomínio Inexistente XYZ")

    send.assert_called_once()
    assert send.call_args[0][2] == REJECT_CONDO_MESSAGE
    assert not Resident.objects.filter(phone_number=phone).exists()
    assert ChatSession.objects.filter(tenant=tenant, phone_number=phone).exists()


@pytest.mark.django_db
def test_onboarding_unknown_condo_lists_all_markets_when_tenant_has_markets():
    tenant = TenantFactory()
    instance = WhatsappInstanceFactory(tenant=tenant)
    m1 = MarketFactory(tenant=tenant, name="Mercado Norte")
    m2 = MarketFactory(tenant=tenant, name="Mercado Sul")
    phone = "5511000111222"
    ChatSessionFactory(
        tenant=tenant,
        phone_number=phone,
        state=ChatSession.State.AWAITING_CONDO,
        temporary_name="João",
    )

    with mock.patch(
        "apps.residents.services.handlers.condo.send_whatsapp_reply",
    ) as send:
        with tenant_scope(tenant.id):
            process_inbound_message(
                tenant.id,
                instance,
                phone,
                "zzzzqqqxxx999inexistente",
            )

    session = ChatSession.objects.get(tenant=tenant, phone_number=phone)
    assert session.state == ChatSession.State.AWAITING_CONDO_SUGGESTION
    suggested = session.context_data.get(SUGGESTED_CONDOS_KEY)
    assert suggested == [
        {"id": m1.id, "name": m1.name},
        {"id": m2.id, "name": m2.name},
    ]
    body = send.call_args[0][2]
    assert "Não encontrei um condomínio com esse nome" in body
    assert f"1 - {m1.name}" in body
    assert f"2 - {m2.name}" in body
    assert not Resident.objects.filter(phone_number=phone).exists()


@pytest.mark.django_db
def test_onboarding_creates_resident_and_opens_main_menu():
    tenant = TenantFactory()
    instance = WhatsappInstanceFactory(tenant=tenant)
    market = MarketFactory(tenant=tenant, name="Residencial Vista Alegre")
    phone = "5511666555444"
    ChatSessionFactory(
        tenant=tenant,
        phone_number=phone,
        state=ChatSession.State.AWAITING_CONDO,
        temporary_name="Carlos",
    )

    with mock.patch("apps.sales.services.main_menu.send_whatsapp_reply") as send:
        with tenant_scope(tenant.id):
            process_inbound_message(tenant.id, instance, phone, "Vista Alegre")

    resident = Resident.objects.get(phone_number=phone)
    assert resident.name == "Carlos"
    assert resident.market_id == market.id
    session = ChatSession.objects.get(tenant=tenant, phone_number=phone)
    assert session.state == ChatSession.State.AWAITING_MAIN_MENU
    body = send.call_args[0][2]
    assert "cadastro foi concluído" in body.lower()
    assert market.name in body
    assert "1 —" in body
    assert "Como posso te ajudar agora?" not in body


@pytest.mark.django_db
def test_onboarding_starts_when_session_was_active_bot_without_resident():
    tenant = TenantFactory()
    instance = WhatsappInstanceFactory(tenant=tenant)
    phone = "5514997426163"
    ChatSessionFactory(
        tenant=tenant,
        phone_number=phone,
        state=ChatSession.State.IDLE,
    )

    with mock.patch("apps.residents.services.onboarding_flow.send_whatsapp_reply") as send:
        with tenant_scope(tenant.id):
            handled = process_inbound_message(tenant.id, instance, phone, "oi")

    assert handled is True
    send.assert_called_once()
    assert "Nome Completo" in send.call_args[0][2]
    session = ChatSession.objects.get(tenant=tenant, phone_number=phone)
    assert session.state == ChatSession.State.AWAITING_NAME


@pytest.mark.django_db
def test_completed_resident_skips_onboarding():
    tenant = TenantFactory()
    instance = WhatsappInstanceFactory(tenant=tenant)
    resident = ResidentFactory(tenant=tenant, phone_number="5511000001111")

    with mock.patch("apps.residents.services.onboarding_flow.send_whatsapp_reply") as send:
        with tenant_scope(tenant.id):
            handled = process_inbound_message(
                tenant.id,
                instance,
                resident.phone_number,
                "quero comprar",
            )

    assert handled is False
    send.assert_not_called()
    assert resident_has_completed_onboarding(tenant.id, resident.phone_number)


@pytest.mark.django_db
def test_find_market_fuzzy_match():
    tenant = TenantFactory()
    market = MarketFactory(tenant=tenant, name="Condomínio Parque das Flores")
    result = match_markets_by_query(tenant.id, "parque flores")
    assert result.kind == "suggestions"
    assert result.suggestions
    assert result.suggestions[0][0].id == market.id
    assert find_market_by_query(tenant.id, "parque flores") is None


@pytest.mark.django_db
def test_find_market_long_phrase_with_condo_name():
    """Usuário digita nome próprio + frase; ainda encontra o condomínio."""
    tenant = TenantFactory()
    market = MarketFactory(tenant=tenant, name="Vila Sônia")
    found = find_market_by_query(
        tenant.id,
        "Antônia Leidiane Condomínio vila Sônia",
    )
    assert found is not None
    assert found.id == market.id


@pytest.mark.django_db
def test_find_market_respects_tenant_isolation():
    tenant_a = TenantFactory()
    tenant_b = TenantFactory()
    MarketFactory(tenant=tenant_b, name="Vila Sônia")
    found = find_market_by_query(tenant_a.id, "Vila Sônia")
    assert found is None
    result = match_markets_by_query(tenant_a.id, "Vila Sônia")
    assert result.kind == "none"


@pytest.mark.django_db
def test_match_no_similarity_returns_list_all_when_markets_exist():
    tenant = TenantFactory()
    a = MarketFactory(tenant=tenant, name="Alpha Residence")
    b = MarketFactory(tenant=tenant, name="Beta Gardens")
    result = match_markets_by_query(tenant.id, "zzzzqqqxxx999inexistente")
    assert result.kind == "list_all"
    ids = {m.id for m, _ in result.suggestions}
    assert ids == {a.id, b.id}


@pytest.mark.django_db
def test_match_no_similarity_returns_none_without_markets():
    tenant = TenantFactory()
    result = match_markets_by_query(tenant.id, "zzzzqqqxxx999inexistente")
    assert result.kind == "none"
    assert result.suggestions == []


@pytest.mark.django_db
def test_onboarding_medium_match_offers_condo_suggestions():
    tenant = TenantFactory()
    instance = WhatsappInstanceFactory(tenant=tenant)
    market = MarketFactory(tenant=tenant, name="Condomínio Parque das Flores")
    phone = "5511555444333"
    ChatSessionFactory(
        tenant=tenant,
        phone_number=phone,
        state=ChatSession.State.AWAITING_CONDO,
        temporary_name="Ana",
    )

    with mock.patch(
        "apps.residents.services.handlers.condo.send_whatsapp_reply",
    ) as send:
        with tenant_scope(tenant.id):
            process_inbound_message(tenant.id, instance, phone, "parque flores")

    session = ChatSession.objects.get(tenant=tenant, phone_number=phone)
    assert session.state == ChatSession.State.AWAITING_CONDO_SUGGESTION
    suggested = session.context_data.get(SUGGESTED_CONDOS_KEY)
    assert suggested == [{"id": market.id, "name": market.name}]
    body = send.call_args[0][2]
    assert "opções parecidas" in body
    assert f"1 - {market.name}" in body
    assert "Cancelar" in body
    assert not Resident.objects.filter(phone_number=phone).exists()


@pytest.mark.django_db
def test_onboarding_condo_suggestion_choice_completes():
    tenant = TenantFactory()
    instance = WhatsappInstanceFactory(tenant=tenant)
    market = MarketFactory(tenant=tenant, name="Asa Norte")
    phone = "5511444333222"
    ChatSessionFactory(
        tenant=tenant,
        phone_number=phone,
        state=ChatSession.State.AWAITING_CONDO_SUGGESTION,
        temporary_name="Bruno",
        context_data={
            SUGGESTED_CONDOS_KEY: [{"id": market.id, "name": market.name}],
        },
    )

    with mock.patch("apps.sales.services.main_menu.send_whatsapp_reply") as send:
        with tenant_scope(tenant.id):
            process_inbound_message(tenant.id, instance, phone, "1")

    resident = Resident.objects.get(phone_number=phone)
    assert resident.market_id == market.id
    assert resident.name == "Bruno"
    session = ChatSession.objects.get(tenant=tenant, phone_number=phone)
    assert session.state == ChatSession.State.AWAITING_MAIN_MENU
    assert session.context_data == {}
    assert market.name in send.call_args[0][2]


@pytest.mark.django_db
def test_onboarding_condo_suggestion_cancel_returns_to_condo():
    tenant = TenantFactory()
    instance = WhatsappInstanceFactory(tenant=tenant)
    market = MarketFactory(tenant=tenant, name="Aviação")
    phone = "5511333222111"
    ChatSessionFactory(
        tenant=tenant,
        phone_number=phone,
        state=ChatSession.State.AWAITING_CONDO_SUGGESTION,
        temporary_name="Carla",
        context_data={
            SUGGESTED_CONDOS_KEY: [{"id": market.id, "name": market.name}],
        },
    )

    with mock.patch(
        "apps.residents.services.handlers.condo.send_whatsapp_reply",
    ) as send:
        with tenant_scope(tenant.id):
            process_inbound_message(tenant.id, instance, phone, "Cancelar")

    session = ChatSession.objects.get(tenant=tenant, phone_number=phone)
    assert session.state == ChatSession.State.AWAITING_CONDO
    assert session.context_data == {}
    assert session.temporary_name == "Carla"
    assert send.call_args[0][2] == RETRY_CONDO_NAME_MESSAGE
    assert not Resident.objects.filter(phone_number=phone).exists()


@pytest.mark.django_db
def test_onboarding_condo_suggestion_invalid_returns_to_condo():
    tenant = TenantFactory()
    instance = WhatsappInstanceFactory(tenant=tenant)
    market = MarketFactory(tenant=tenant, name="Asa Sul")
    phone = "5511222111000"
    ChatSessionFactory(
        tenant=tenant,
        phone_number=phone,
        state=ChatSession.State.AWAITING_CONDO_SUGGESTION,
        temporary_name="Diego",
        context_data={
            SUGGESTED_CONDOS_KEY: [{"id": market.id, "name": market.name}],
        },
    )

    with mock.patch(
        "apps.residents.services.handlers.condo.send_whatsapp_reply",
    ) as send:
        with tenant_scope(tenant.id):
            process_inbound_message(tenant.id, instance, phone, "9")

    session = ChatSession.objects.get(tenant=tenant, phone_number=phone)
    assert session.state == ChatSession.State.AWAITING_CONDO
    assert session.context_data == {}
    assert send.call_args[0][2] == RETRY_CONDO_NAME_MESSAGE


@pytest.mark.django_db
def test_onboarding_condo_suggestion_choice_double_digit():
    tenant = TenantFactory()
    instance = WhatsappInstanceFactory(tenant=tenant)
    markets = [
        MarketFactory(tenant=tenant, name=f"Condomínio Opção {i:02d}")
        for i in range(1, 13)
    ]
    chosen = markets[11]
    phone = "5511111222333"
    ChatSessionFactory(
        tenant=tenant,
        phone_number=phone,
        state=ChatSession.State.AWAITING_CONDO_SUGGESTION,
        temporary_name="Elena",
        context_data={
            SUGGESTED_CONDOS_KEY: [
                {"id": m.id, "name": m.name} for m in markets
            ],
        },
    )

    with mock.patch("apps.sales.services.main_menu.send_whatsapp_reply") as send:
        with tenant_scope(tenant.id):
            process_inbound_message(tenant.id, instance, phone, "12")

    resident = Resident.objects.get(phone_number=phone)
    assert resident.market_id == chosen.id
    assert resident.name == "Elena"
    session = ChatSession.objects.get(tenant=tenant, phone_number=phone)
    assert session.state == ChatSession.State.AWAITING_MAIN_MENU
    assert chosen.name in send.call_args[0][2]


@pytest.mark.django_db
def test_parse_evolution_payload_extracts_text():
    body = {
        "event": "MESSAGE",
        "instance": "mc-test",
        "data": {
            "key": {"remoteJid": "5511999999999@s.whatsapp.net", "id": "msg1", "fromMe": False},
            "message": {"conversation": "Olá mundo"},
        },
    }
    event = parse_evolution_payload(body)
    assert event is not None
    assert event.message_text == "Olá mundo"


@pytest.mark.django_db
def test_residents_list_tenant_isolation(api_client):
    tenant_a = TenantFactory()
    tenant_b = TenantFactory()
    user_a = UserFactory(tenant=tenant_a, email="res-a@example.com")
    ResidentFactory(tenant=tenant_b, phone_number="5511999990001", name="Outro")

    _auth(api_client, user_a)
    response = api_client.get(reverse("residents-list"))
    assert response.status_code == 200
    phones = [r["phone_number"] for r in response.json()]
    assert "5511999990001" not in phones


@pytest.mark.django_db
def test_residents_list_filter_by_name_and_phone(api_client):
    tenant = TenantFactory()
    user = UserFactory(tenant=tenant, email="res-filter@example.com")
    market = MarketFactory(tenant=tenant, name="Condomínio Sol")
    ResidentFactory(
        tenant=tenant,
        market=market,
        name="Ana Paula",
        phone_number="5511988776655",
    )
    ResidentFactory(
        tenant=tenant,
        market=market,
        name="Bruno Costa",
        phone_number="5511977665544",
    )

    _auth(api_client, user)
    by_name = api_client.get(reverse("residents-list"), {"name": "ana"})
    assert by_name.status_code == 200
    assert len(by_name.json()) == 1
    assert by_name.json()[0]["name"] == "Ana Paula"

    by_phone = api_client.get(reverse("residents-list"), {"phone": "(11) 98877-6655"})
    assert by_phone.status_code == 200
    assert len(by_phone.json()) == 1
    assert by_phone.json()[0]["phone_number"] == "5511988776655"


@pytest.mark.django_db
def test_residents_patch_market(api_client):
    tenant = TenantFactory()
    user = UserFactory(tenant=tenant, email="res-patch@example.com")
    market_a = MarketFactory(tenant=tenant, name="Mercado A")
    market_b = MarketFactory(tenant=tenant, name="Mercado B")
    resident = ResidentFactory(tenant=tenant, market=market_a)

    _auth(api_client, user)
    response = api_client.patch(
        reverse("residents-detail", kwargs={"pk": resident.id}),
        {"market_id": market_b.id},
        format="json",
    )
    assert response.status_code == 200
    assert response.json()["market"]["id"] == market_b.id

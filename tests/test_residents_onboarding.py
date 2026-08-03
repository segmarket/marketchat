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
from apps.residents.services.condo_match import find_market_by_query
from apps.residents.services.greeting import greeting_for_now
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


def _ai(
    *,
    nome=None,
    condominio=None,
    intencao_primaria="cadastro_simples",
    acao_imediata_codigo="continuar_onboarding",
    resposta_texto="",
):
    from apps.residents.services.onboarding_ai import OnboardingAIResult

    return OnboardingAIResult(
        nome=nome,
        condominio=condominio,
        intencao_primaria=intencao_primaria,
        acao_imediata_codigo=acao_imediata_codigo,
        resposta_texto=resposta_texto,
    )


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
        with mock.patch(
            "apps.residents.services.onboarding_flow.analyze_onboarding_message",
            return_value=None,
        ):
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
        with mock.patch(
            "apps.residents.services.onboarding_flow.analyze_onboarding_message",
            return_value=None,
        ):
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
        with mock.patch(
            "apps.residents.services.onboarding_flow.analyze_onboarding_message",
            return_value=None,
        ):
            with tenant_scope(tenant.id):
                process_inbound_message(tenant.id, instance, phone, "Condomínio Inexistente XYZ")

    send.assert_called_once()
    assert send.call_args[0][2] == REJECT_CONDO_MESSAGE
    assert not Resident.objects.filter(phone_number=phone).exists()
    assert ChatSession.objects.filter(tenant=tenant, phone_number=phone).exists()


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

    with mock.patch(
        "apps.residents.services.onboarding_flow.analyze_onboarding_message",
        return_value=None,
    ):
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
        with mock.patch(
            "apps.residents.services.onboarding_flow.analyze_onboarding_message",
            return_value=None,
        ):
            with tenant_scope(tenant.id):
                handled = process_inbound_message(tenant.id, instance, phone, "oi")

    assert handled is True
    send.assert_called_once()
    assert "como posso te chamar" in send.call_args[0][2].lower() or "qual o seu nome" in send.call_args[0][2].lower()
    session = ChatSession.objects.get(tenant=tenant, phone_number=phone)
    assert session.state == ChatSession.State.AWAITING_NAME


@pytest.mark.django_db
def test_onboarding_ai_extracts_name_and_condo_opens_menu_without_duplicate_ask():
    tenant = TenantFactory()
    instance = WhatsappInstanceFactory(tenant=tenant)
    market = MarketFactory(tenant=tenant, name="Villa Bella")
    phone = "5511988776655"

    ai_result = _ai(
        nome="Juliana",
        condominio="Villa Bella",
        intencao_primaria="cadastro_simples",
        acao_imediata_codigo="continuar_onboarding",
        resposta_texto="",
    )

    with mock.patch(
        "apps.residents.services.onboarding_flow.analyze_onboarding_message",
        return_value=ai_result,
    ):
        with mock.patch("apps.residents.services.onboarding_flow.send_whatsapp_reply") as send_onboarding:
            with mock.patch("apps.sales.services.main_menu.send_whatsapp_reply") as send_menu:
                with tenant_scope(tenant.id):
                    handled = process_inbound_message(
                        tenant.id,
                        instance,
                        phone,
                        "Sou a Juliana do Villa Bella",
                    )

    assert handled is True
    resident = Resident.objects.get(phone_number=phone)
    assert resident.name == "Juliana"
    assert resident.market_id == market.id
    session = ChatSession.objects.get(tenant=tenant, phone_number=phone)
    assert session.state == ChatSession.State.AWAITING_MAIN_MENU
    assert session.pending_intent == ""
    # Só privacidade no onboarding; NÃO envia resposta_texto pedindo dado
    assert send_onboarding.call_count == 1
    assert "privacidade" in send_onboarding.call_args[0][2].lower()
    assert send_menu.called
    assert "cadastro foi concluído" in send_menu.call_args[0][2].lower()


@pytest.mark.django_db
def test_onboarding_ai_reclamacao_resumes_product_issue_without_main_menu():
    from apps.sales.services.whatsapp_interactive import MENU_PRODUCT, SUPPORT_DETAILS_PROMPT

    tenant = TenantFactory()
    instance = WhatsappInstanceFactory(tenant=tenant)
    market = MarketFactory(tenant=tenant, name="Portal")
    phone = "5511988001122"

    ai_result = _ai(
        nome="Diego",
        condominio="Portal",
        intencao_primaria="reclamacao",
        acao_imediata_codigo="continuar_onboarding",
        resposta_texto="",
    )

    with mock.patch(
        "apps.residents.services.onboarding_flow.analyze_onboarding_message",
        return_value=ai_result,
    ):
        with mock.patch("apps.residents.services.onboarding_flow.send_whatsapp_reply") as send_onboarding:
            with mock.patch("apps.sales.services.main_menu.send_whatsapp_reply") as send_menu:
                with tenant_scope(tenant.id):
                    process_inbound_message(
                        tenant.id,
                        instance,
                        phone,
                        "Oi, sou o Diego do Portal, estou com produto vencido",
                    )

    session = ChatSession.objects.get(tenant=tenant, phone_number=phone)
    assert session.state == ChatSession.State.AWAITING_SUPPORT_DETAILS
    assert session.temporary_name == MENU_PRODUCT
    assert session.pending_intent == ""
    assert Resident.objects.filter(phone_number=phone, market=market).exists()

    # Privacidade + intro/transição no onboarding; prompt de suporte via main_menu
    assert send_onboarding.call_count == 2
    transition_body = send_onboarding.call_args_list[1][0][2]
    assert "cadastro foi concluído" in transition_body.lower()
    assert "retomando o assunto" in transition_body.lower()
    assert "como posso ajudar" not in transition_body.lower()
    assert send_menu.call_count == 1
    assert send_menu.call_args[0][2] == SUPPORT_DETAILS_PROMPT


@pytest.mark.django_db
def test_onboarding_preserves_reclamacao_intent_until_condo_complete():
    from apps.sales.services.whatsapp_interactive import MENU_PRODUCT

    tenant = TenantFactory()
    instance = WhatsappInstanceFactory(tenant=tenant)
    market = MarketFactory(tenant=tenant, name="Portal")
    phone = "5511988112233"

    first = _ai(
        nome="Diego",
        condominio=None,
        intencao_primaria="reclamacao",
        acao_imediata_codigo="continuar_onboarding",
        resposta_texto="Sinto muito! Qual o nome do seu condomínio?",
    )
    second = _ai(
        nome=None,
        condominio="Portal",
        intencao_primaria="cadastro_simples",
        acao_imediata_codigo="continuar_onboarding",
        resposta_texto="",
    )

    with mock.patch(
        "apps.residents.services.onboarding_flow.analyze_onboarding_message",
        side_effect=[first, second],
    ):
        with mock.patch("apps.residents.services.onboarding_flow.send_whatsapp_reply"):
            with mock.patch("apps.sales.services.main_menu.send_whatsapp_reply"):
                with tenant_scope(tenant.id):
                    process_inbound_message(
                        tenant.id,
                        instance,
                        phone,
                        "Oi, sou o Diego, leite vencido",
                    )
                    session_mid = ChatSession.objects.get(tenant=tenant, phone_number=phone)
                    assert session_mid.pending_intent == "reclamacao"
                    assert session_mid.state == ChatSession.State.AWAITING_CONDO

                    process_inbound_message(tenant.id, instance, phone, "Portal")

    session = ChatSession.objects.get(tenant=tenant, phone_number=phone)
    assert session.state == ChatSession.State.AWAITING_SUPPORT_DETAILS
    assert session.temporary_name == MENU_PRODUCT
    assert session.pending_intent == ""
    assert Resident.objects.get(phone_number=phone).market_id == market.id


@pytest.mark.django_db
def test_onboarding_ai_name_only_awaits_condo():
    tenant = TenantFactory()
    instance = WhatsappInstanceFactory(tenant=tenant)
    phone = "5511977665544"

    ai_result = _ai(
        nome="Pedro Santos",
        condominio=None,
        intencao_primaria="duvida",
        acao_imediata_codigo="continuar_onboarding",
        resposta_texto="Oi Pedro! Pode me dizer o nome do seu condomínio?",
    )

    with mock.patch(
        "apps.residents.services.onboarding_flow.analyze_onboarding_message",
        return_value=ai_result,
    ):
        with mock.patch("apps.residents.services.onboarding_flow.send_whatsapp_reply") as send:
            with tenant_scope(tenant.id):
                process_inbound_message(
                    tenant.id,
                    instance,
                    phone,
                    "Oi, sou o Pedro Santos, quanto custa a água?",
                )

    session = ChatSession.objects.get(tenant=tenant, phone_number=phone)
    assert session.state == ChatSession.State.AWAITING_CONDO
    assert session.temporary_name == "Pedro Santos"
    assert session.pending_intent == "duvida"
    assert not Resident.objects.filter(phone_number=phone).exists()
    assert send.call_count == 2
    assert "condomínio" in send.call_args_list[1][0][2].lower()


@pytest.mark.django_db
def test_onboarding_ai_extracts_bruna_from_sentence_in_awaiting_name():
    tenant = TenantFactory()
    instance = WhatsappInstanceFactory(tenant=tenant)
    phone = "5511911223344"
    ChatSessionFactory(
        tenant=tenant,
        phone_number=phone,
        state=ChatSession.State.AWAITING_NAME,
        temporary_name="",
    )

    ai_result = _ai(
        nome="Bruna",
        condominio=None,
        intencao_primaria="duvida",
        acao_imediata_codigo="continuar_onboarding",
        resposta_texto="Oi Bruna! O mercado funciona 24h. Qual o nome do seu condomínio?",
    )

    with mock.patch(
        "apps.residents.services.onboarding_flow.analyze_onboarding_message",
        return_value=ai_result,
    ):
        with mock.patch("apps.residents.services.onboarding_flow.send_whatsapp_reply") as send:
            with tenant_scope(tenant.id):
                process_inbound_message(
                    tenant.id,
                    instance,
                    phone,
                    "Oi, eu sou a Bruna. Como funciona o mercado?",
                )

    session = ChatSession.objects.get(tenant=tenant, phone_number=phone)
    assert session.temporary_name == "Bruna"
    assert session.state == ChatSession.State.AWAITING_CONDO
    assert send.call_count == 1
    assert "Bruna" in send.call_args[0][2]


@pytest.mark.django_db
def test_onboarding_ignores_vendas_spam_without_reply():
    tenant = TenantFactory()
    instance = WhatsappInstanceFactory(tenant=tenant)
    phone = "5511900112233"

    ai_result = _ai(
        intencao_primaria="vendas_spam",
        acao_imediata_codigo="ignorar_mensagem",
        resposta_texto="",
    )

    with mock.patch(
        "apps.residents.services.onboarding_flow.analyze_onboarding_message",
        return_value=ai_result,
    ):
        with mock.patch("apps.residents.services.onboarding_flow.send_whatsapp_reply") as send:
            with tenant_scope(tenant.id):
                handled = process_inbound_message(
                    tenant.id,
                    instance,
                    phone,
                    "O investimento fica em torno de R$ 250 por projeto 3D",
                )

    assert handled is True
    send.assert_not_called()
    assert not Resident.objects.filter(phone_number=phone).exists()
    # Não muta FSM de onboarding
    session = ChatSession.objects.filter(tenant=tenant, phone_number=phone).first()
    if session is not None:
        assert session.state not in {
            ChatSession.State.AWAITING_NAME,
            ChatSession.State.AWAITING_CONDO,
            ChatSession.State.WAITING_FOR_HUMAN,
        }


@pytest.mark.django_db
def test_onboarding_audio_transcription_transfers_to_human():
    tenant = TenantFactory()
    instance = WhatsappInstanceFactory(tenant=tenant)
    phone = "5511900223344"

    ai_result = _ai(
        intencao_primaria="transcricao_audio",
        acao_imediata_codigo="pausar_bot_transferir",
        resposta_texto=(
            "Entendi que você precisa detalhar melhor a situação. "
            "Vou pausar o assistente virtual e transferir seu atendimento "
            "para a nossa equipe humana. Aguarde um instante!"
        ),
    )

    with mock.patch(
        "apps.residents.services.onboarding_flow.analyze_onboarding_message",
        return_value=ai_result,
    ):
        with mock.patch("apps.residents.services.onboarding_flow.send_whatsapp_reply") as send:
            with tenant_scope(tenant.id):
                process_inbound_message(
                    tenant.id,
                    instance,
                    phone,
                    "*Transcrição* Oi. Bom, o sistema continua do mesmo jeito...",
                )

    session = ChatSession.objects.get(tenant=tenant, phone_number=phone)
    assert session.state == ChatSession.State.WAITING_FOR_HUMAN
    assert session.is_bot_active is False
    send.assert_called_once()
    assert "equipe humana" in send.call_args[0][2].lower() or "atendente" in send.call_args[0][2].lower()
    assert not Resident.objects.filter(phone_number=phone).exists()


@pytest.mark.django_db
def test_onboarding_fallback_does_not_save_long_sentence_as_name():
    tenant = TenantFactory()
    instance = WhatsappInstanceFactory(tenant=tenant)
    phone = "5511933445566"
    ChatSessionFactory(
        tenant=tenant,
        phone_number=phone,
        state=ChatSession.State.AWAITING_NAME,
        temporary_name="",
    )

    with mock.patch(
        "apps.residents.services.onboarding_flow.analyze_onboarding_message",
        return_value=None,
    ):
        with mock.patch("apps.residents.services.onboarding_flow.send_whatsapp_reply") as send:
            with tenant_scope(tenant.id):
                process_inbound_message(
                    tenant.id,
                    instance,
                    phone,
                    "Oi, eu sou a Bruna. Como funciona o mercado?",
                )

    session = ChatSession.objects.get(tenant=tenant, phone_number=phone)
    assert session.state == ChatSession.State.AWAITING_NAME
    assert session.temporary_name == ""
    assert "como te chamar" in send.call_args[0][2].lower() or "nome" in send.call_args[0][2].lower()


@pytest.mark.django_db
def test_onboarding_ai_failure_falls_back_to_rigid_flow():
    tenant = TenantFactory()
    instance = WhatsappInstanceFactory(tenant=tenant)
    phone = "5511966554433"

    with mock.patch(
        "apps.residents.services.onboarding_flow.analyze_onboarding_message",
        return_value=None,
    ):
        with mock.patch("apps.residents.services.onboarding_flow.send_whatsapp_reply") as send:
            with tenant_scope(tenant.id):
                process_inbound_message(tenant.id, instance, phone, "quero comprar cocada")

    send.assert_called_once()
    body = send.call_args[0][2]
    assert "privacidade" in body.lower()
    assert "qual o seu nome" in body.lower()
    session = ChatSession.objects.get(tenant=tenant, phone_number=phone)
    assert session.state == ChatSession.State.AWAITING_NAME


@pytest.mark.django_db
def test_onboarding_ai_connection_error_returns_soft_fallback():
    from apps.residents.services.onboarding_ai import (
        ONBOARDING_AI_SOFT_FALLBACK_TEXT,
        analyze_onboarding_message,
    )

    with (
        mock.patch(
            "apps.residents.services.onboarding_ai.settings.OPENAI_API_KEY",
            "sk-test",
        ),
        mock.patch(
            "apps.chatbot.services.chatbot_core._get_client",
            side_effect=ConnectionError("Temporary failure in name resolution"),
        ),
    ):
        result = analyze_onboarding_message("oi")

    assert result is not None
    assert result.nome is None
    assert result.condominio is None
    assert result.intencao_primaria == "duvida"
    assert result.acao_imediata_codigo == "continuar_onboarding"
    assert result.resposta_texto == ONBOARDING_AI_SOFT_FALLBACK_TEXT


@pytest.mark.django_db
def test_onboarding_ai_soft_fallback_is_sent_on_openai_failure():
    from apps.residents.services.onboarding_ai import ONBOARDING_AI_SOFT_FALLBACK_TEXT

    tenant = TenantFactory()
    instance = WhatsappInstanceFactory(tenant=tenant)
    phone = "5511966554499"

    with (
        mock.patch(
            "apps.residents.services.onboarding_ai.settings.OPENAI_API_KEY",
            "sk-test",
        ),
        mock.patch(
            "apps.chatbot.services.chatbot_core._get_client",
            side_effect=ConnectionError("Temporary failure in name resolution"),
        ),
        mock.patch("apps.residents.services.onboarding_flow.send_whatsapp_reply") as send,
    ):
        with tenant_scope(tenant.id):
            process_inbound_message(tenant.id, instance, phone, "oi")

    texts = [call.args[2] for call in send.call_args_list]
    assert any(ONBOARDING_AI_SOFT_FALLBACK_TEXT in t for t in texts)
    assert any("privacidade" in t.lower() for t in texts)
    session = ChatSession.objects.get(tenant=tenant, phone_number=phone)
    assert session.state == ChatSession.State.AWAITING_NAME


@pytest.mark.django_db
def test_onboarding_ai_parse_allows_empty_resposta_for_spam():
    from apps.residents.services.onboarding_ai import _parse_payload

    result = _parse_payload(
        {
            "nome": None,
            "condominio": None,
            "intencao_primaria": "vendas_spam",
            "acao_imediata_codigo": "ignorar_mensagem",
            "resposta_texto": "",
        }
    )
    assert result is not None
    assert result.acao_imediata_codigo == "ignorar_mensagem"
    assert result.resposta_texto == ""


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
    found = find_market_by_query(tenant.id, "parque flores")
    assert found is not None
    assert found.id == market.id


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

from unittest import mock

import pytest

from apps.residents.models import ChatSession
from apps.residents.services.onboarding_ai import (
    OnboardingAIResult,
    _parse_payload,
)
from apps.residents.services.onboarding_flow import process_inbound_message
from apps.sales.services.intent_gatekeeper import PAYMENT_ERROR, classify_user_intent
from apps.sales.services.maquininha_backup import (
    HUMAN_QUEUE_PURCHASE_ESCAPE_MESSAGE,
    MACHINE_BACKUP_SALE_MESSAGE,
    try_escape_human_queue_for_purchase,
)
from apps.tenants.context import tenant_scope
from tests.factories import (
    ChatSessionFactory,
    MarketFactory,
    ResidentFactory,
    TenantFactory,
    WhatsappInstanceFactory,
)


def test_parse_problema_maquininha_iniciar_venda_backup():
    result = _parse_payload(
        {
            "nome": None,
            "condominio": None,
            "intencao_primaria": "problema_maquininha",
            "acao_imediata_codigo": "iniciar_venda_backup",
            "resposta_texto": "",
        }
    )
    assert result is not None
    assert result.intencao_primaria == "problema_maquininha"
    assert result.acao_imediata_codigo == "iniciar_venda_backup"
    assert result.resposta_texto == ""


def test_heuristic_maquina_fora_is_payment_error():
    assert (
        classify_user_intent("a maquina esta fora nao consigo pagar") == PAYMENT_ERROR
    )
    assert classify_user_intent("A maquininha não passou o cartão") == PAYMENT_ERROR
    assert classify_user_intent("totem offline") == PAYMENT_ERROR


@pytest.mark.django_db
def test_start_maquininha_backup_sale_opens_product_search():
    tenant = TenantFactory()
    market = MarketFactory(tenant=tenant, name="Portal")
    instance = WhatsappInstanceFactory(tenant=tenant)
    phone = "5511999000011"
    resident = ResidentFactory(
        tenant=tenant, phone_number=phone, market=market, name="Ana"
    )
    session = ChatSessionFactory(
        tenant=tenant,
        phone_number=phone,
        state=ChatSession.State.IDLE,
    )

    from apps.sales.services.maquininha_backup import start_maquininha_backup_sale

    with (
        mock.patch(
            "apps.sales.services.maquininha_backup.notify_owner_support_issue"
        ),
        mock.patch(
            "apps.sales.services.maquininha_backup.create_critical_panel_notification"
        ),
        mock.patch("apps.sales.services.maquininha_backup.send_whatsapp_reply") as send_sale,
        mock.patch("apps.sales.services.maquininha_backup.append_assistant_message"),
        tenant_scope(tenant.id),
    ):
        start_maquininha_backup_sale(
            instance=instance,
            tenant_id=tenant.id,
            phone=phone,
            resident=resident,
            session=session,
            message="maquina fora",
        )
        session.refresh_from_db()

    assert session.state == ChatSession.State.PRODUCT_SEARCH
    assert session.active_cart_id is not None
    assert send_sale.call_args[0][2] == MACHINE_BACKUP_SALE_MESSAGE


@pytest.mark.django_db
def test_onboarding_ai_backup_during_cadastro_sets_pending_intent():
    tenant = TenantFactory()
    MarketFactory(tenant=tenant, name="Portal")
    instance = WhatsappInstanceFactory(tenant=tenant)
    phone = "5511999000022"

    ai = OnboardingAIResult(
        nome=None,
        condominio=None,
        intencao_primaria="problema_maquininha",
        acao_imediata_codigo="iniciar_venda_backup",
        resposta_texto="",
    )

    with (
        mock.patch(
            "apps.residents.services.onboarding_flow.analyze_onboarding_message",
            return_value=ai,
        ),
        mock.patch("apps.residents.services.onboarding_flow.send_whatsapp_reply") as send,
    ):
        with tenant_scope(tenant.id):
            process_inbound_message(tenant.id, instance, phone, "maquina fora")

    session = ChatSession.objects.get(tenant=tenant, phone_number=phone)
    assert session.pending_intent == "problema_maquininha"
    assert session.state == ChatSession.State.AWAITING_NAME
    assert send.call_count >= 1


@pytest.mark.django_db
def test_escape_human_queue_on_purchase_keywords():
    tenant = TenantFactory()
    market = MarketFactory(tenant=tenant)
    instance = WhatsappInstanceFactory(tenant=tenant)
    phone = "5511999000033"
    resident = ResidentFactory(
        tenant=tenant, phone_number=phone, market=market, name="Bruno"
    )
    session = ChatSessionFactory(
        tenant=tenant,
        phone_number=phone,
        state=ChatSession.State.WAITING_FOR_HUMAN,
        is_bot_active=False,
    )

    with (
        mock.patch("apps.sales.services.maquininha_backup.send_whatsapp_reply") as send,
        mock.patch("apps.sales.services.maquininha_backup.append_assistant_message"),
        tenant_scope(tenant.id),
    ):
        ok = try_escape_human_queue_for_purchase(
            instance=instance,
            phone=phone,
            text="quero comprar com pix",
            session=session,
            resident=resident,
        )

    assert ok is True
    session.refresh_from_db()
    assert session.is_bot_active is True
    assert session.state == ChatSession.State.PRODUCT_SEARCH
    assert session.active_cart_id is not None
    assert send.call_args[0][2] == HUMAN_QUEUE_PURCHASE_ESCAPE_MESSAGE


@pytest.mark.django_db
def test_escape_human_queue_silent_without_keywords():
    tenant = TenantFactory()
    market = MarketFactory(tenant=tenant)
    instance = WhatsappInstanceFactory(tenant=tenant)
    phone = "5511999000044"
    resident = ResidentFactory(
        tenant=tenant, phone_number=phone, market=market, name="Carla"
    )
    session = ChatSessionFactory(
        tenant=tenant,
        phone_number=phone,
        state=ChatSession.State.WAITING_FOR_HUMAN,
        is_bot_active=False,
    )

    with tenant_scope(tenant.id):
        ok = try_escape_human_queue_for_purchase(
            instance=instance,
            phone=phone,
            text="obrigado, aguardo",
            session=session,
            resident=resident,
        )

    assert ok is False
    session.refresh_from_db()
    assert session.state == ChatSession.State.WAITING_FOR_HUMAN
    assert session.is_bot_active is False

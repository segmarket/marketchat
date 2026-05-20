from unittest import mock

import pytest

from apps.chatbot.services.chatbot_core import (
    OCCURRENCE_COMMAND_TAGS,
    STATIC_COMPLAINT_ASSISTANT,
    STATIC_GENERAL_ASSISTANT,
)
from apps.chatbot.services.occurrence_dispatch import dispatch_occurrence_tag
from apps.chatbot.services.occurrence_tags import (
    parse_occurrence_tag,
    process_ai_assistant_reply,
)
from apps.notifications.models import Notification
from tests.factories import (
    ChatSessionFactory,
    ResidentFactory,
    TenantFactory,
    WhatsappInstanceFactory,
)


def test_parse_occurrence_tag_extracts_tag_and_clean_text():
    tag, clean = parse_occurrence_tag(
        "[ALERTA_QUALIDADE] Poxa, João! Lamento muito pelo produto estragado."
    )
    assert tag == "ALERTA_QUALIDADE"
    assert clean == "Poxa, João! Lamento muito pelo produto estragado."
    assert "[" not in clean


def test_parse_occurrence_tag_without_tag_returns_original():
    text = "Olá! Como posso ajudar?"
    tag, clean = parse_occurrence_tag(text)
    assert tag is None
    assert clean == text


def test_parse_occurrence_tag_unknown_tag_ignored():
    tag, clean = parse_occurrence_tag("[TAG_INVALIDA] Mensagem aqui.")
    assert tag is None
    assert "Mensagem aqui" in clean


def test_static_general_assistant_includes_occurrence_matrix():
    assert "MATRIZ DE RESOLUÇÃO" in STATIC_GENERAL_ASSISTANT
    assert "ALERTA_QUALIDADE" in STATIC_GENERAL_ASSISTANT
    assert "SOLICITACAO_PIX" in STATIC_GENERAL_ASSISTANT
    assert "CATEGORIA 1" in STATIC_GENERAL_ASSISTANT
    assert "gírias provocativas" not in STATIC_GENERAL_ASSISTANT


def test_static_complaint_assistant_includes_occurrence_matrix():
    assert "ALERTA_QUALIDADE" in STATIC_COMPLAINT_ASSISTANT
    assert "FORMATO DE SAÍDA OBRIGATÓRIO" in STATIC_COMPLAINT_ASSISTANT


def test_occurrence_command_tags_set():
    assert "ALERTA_ESTOQUE" in OCCURRENCE_COMMAND_TAGS
    assert len(OCCURRENCE_COMMAND_TAGS) == 8


@pytest.mark.django_db
def test_dispatch_occurrence_tag_creates_panel_notification():
    tenant = TenantFactory()
    instance = WhatsappInstanceFactory(tenant=tenant)
    resident = ResidentFactory(tenant=tenant, name="João Silva")
    session = ChatSessionFactory(tenant=tenant, phone_number=resident.phone_number)

    with mock.patch(
        "apps.chatbot.services.occurrence_dispatch.notify_owner_support_issue",
    ) as notify_owner:
        dispatch_occurrence_tag(
            tag="ALERTA_QUALIDADE",
            tenant_id=tenant.id,
            instance=instance,
            resident=resident,
            session=session,
            user_message="Iogurte vencido",
        )

    notify_owner.assert_called_once()
    note = Notification.all_objects.filter(tenant=tenant, intent_type="ALERTA_QUALIDADE").first()
    assert note is not None
    assert note.severity == Notification.Severity.CRITICAL


@pytest.mark.django_db
def test_dispatch_solicitacao_pix_starts_product_search():
    tenant = TenantFactory()
    instance = WhatsappInstanceFactory(tenant=tenant)
    resident = ResidentFactory(tenant=tenant)
    session = ChatSessionFactory(
        tenant=tenant,
        phone_number=resident.phone_number,
        state="IDLE",
    )

    dispatch_occurrence_tag(
        tag="SOLICITACAO_PIX",
        tenant_id=tenant.id,
        instance=instance,
        resident=resident,
        session=session,
        user_message="Peguei coisas, manda o pix",
    )

    session.refresh_from_db()
    assert session.state == "PRODUCT_SEARCH"
    assert session.active_cart_id is not None
    assert Notification.all_objects.filter(intent_type="SOLICITACAO_PIX").count() == 0


@pytest.mark.django_db
def test_process_ai_assistant_reply_strips_tag_and_records_clean_history():
    tenant = TenantFactory()
    instance = WhatsappInstanceFactory(tenant=tenant)
    resident = ResidentFactory(tenant=tenant)
    session = ChatSessionFactory(tenant=tenant, phone_number=resident.phone_number)

    with mock.patch(
        "apps.chatbot.services.occurrence_tags.dispatch_occurrence_tag",
    ) as dispatch:
        body, tag = process_ai_assistant_reply(
            raw_reply="[ALERTA_INFRA] Obrigado por avisar, João!",
            session=session,
            tenant_id=tenant.id,
            instance=instance,
            resident=resident,
            user_message="Geladeira quebrada",
        )

    assert tag == "ALERTA_INFRA"
    assert body == "Obrigado por avisar, João!"
    assert "[" not in body
    dispatch.assert_called_once()

    from apps.residents.models import ChatMessage

    last = (
        ChatMessage.objects.filter(session=session, role=ChatMessage.Role.ASSISTANT)
        .order_by("-id")
        .first()
    )
    assert last is not None
    assert last.content == body
    assert "[" not in last.content

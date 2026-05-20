from unittest import mock

import pytest

from apps.chatbot.services.chat_history import append_message, get_sliding_history
from apps.chatbot.services.chatbot_core import (
    GATEKEEPER_TAGS,
    STATIC_GENERAL_ASSISTANT,
    classify_gatekeeper_intent,
    complete_with_session_history,
    parse_gatekeeper_tag,
)
from apps.residents.models import ChatMessage, ChatSession
from tests.factories import ChatSessionFactory, TenantFactory


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("PURCHASE", "PURCHASE"),
        ("  payment_error  ", "PAYMENT_ERROR"),
        ("GENERAL\n", "GENERAL"),
        ("", "GENERAL"),
        ("xyz", "GENERAL"),
    ],
)
def test_parse_gatekeeper_tag(raw, expected):
    assert parse_gatekeeper_tag(raw) == expected


def test_static_general_assistant_tone_calibration():
    assert "ANTI-ABUSO" in STATIC_GENERAL_ASSISTANT
    assert "exclusivamente para processar compras" in STATIC_GENERAL_ASSISTANT
    assert "E ae" in STATIC_GENERAL_ASSISTANT
    assert "como mando o pix" in STATIC_GENERAL_ASSISTANT.lower()
    assert "ESCOPO DO MARKETCHAT" in STATIC_GENERAL_ASSISTANT
    assert "MATRIZ DE RESOLUÇÃO" in STATIC_GENERAL_ASSISTANT
    assert "ALERTA_QUALIDADE" in STATIC_GENERAL_ASSISTANT
    assert "gírias provocativas" not in STATIC_GENERAL_ASSISTANT
    assert "corte o assunto imediatamente" not in STATIC_GENERAL_ASSISTANT


def test_gatekeeper_static_system_includes_casual_pix_purchase_examples():
    from apps.chatbot.services.chatbot_core import GATEKEEPER_STATIC_SYSTEM

    assert "como mando o pix" in GATEKEEPER_STATIC_SYSTEM.lower()
    assert "pagar no pix" in GATEKEEPER_STATIC_SYSTEM.lower()


@pytest.mark.django_db
def test_classify_gatekeeper_plain_text(settings):
    settings.OPENAI_API_KEY = "test-key"
    with mock.patch(
        "apps.chatbot.services.chatbot_core.complete_plain",
        return_value="PAYMENT_ERROR",
    ) as complete:
        tag = classify_gatekeeper_intent("A máquina de pagar está com problemas")

    assert tag == "PAYMENT_ERROR"
    complete.assert_called_once()
    call_kwargs = complete.call_args.kwargs
    assert "response_format" not in call_kwargs
    assert "PURCHASE" in call_kwargs["static_system"]
    assert call_kwargs.get("apply_conciseness_rule") is False


@pytest.mark.django_db
def test_sliding_history_limits_to_six_messages(settings):
    settings.OPENAI_HISTORY_WINDOW = 6
    session = ChatSessionFactory()
    for i in range(10):
        role = ChatMessage.Role.USER if i % 2 == 0 else ChatMessage.Role.ASSISTANT
        append_message(session, role=role, content=f"msg-{i}")

    history = get_sliding_history(session)
    assert len(history) == 6
    assert history[0]["content"] == "msg-4"
    assert history[-1]["content"] == "msg-9"


@pytest.mark.django_db
def test_complete_with_session_history_puts_user_last(settings):
    settings.OPENAI_API_KEY = "test-key"
    session = ChatSessionFactory()

    with mock.patch("apps.chatbot.services.chatbot_core._get_client") as get_client:
        mock_client = mock.Mock()
        get_client.return_value = mock_client
        mock_client.chat.completions.create.return_value = mock.Mock(
            choices=[mock.Mock(message=mock.Mock(content="Resposta curta."))],
        )

        reply = complete_with_session_history(
            session=session,
            static_system="Instruções estáticas.",
            user_content="Oi",
            dynamic_system_tail="Morador: Maria",
            max_tokens=80,
        )

    assert reply == "Resposta curta."
    messages = mock_client.chat.completions.create.call_args.kwargs["messages"]
    assert messages[0]["role"] == "system"
    assert "REGRA DE OURO" in messages[0]["content"]
    assert messages[-1]["role"] == "user"
    assert messages[-1]["content"] == "Oi"
    assert mock_client.chat.completions.create.call_args.kwargs["max_tokens"] == 80

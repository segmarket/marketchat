from unittest import mock

import pytest
from django.urls import reverse
from rest_framework_simplejwt.tokens import RefreshToken

from apps.support.services.copilot import SupportCopilotError, complete_support_chat
from apps.support.services.route_context import resolve_route_context
from tests.factories import UserFactory


def _auth(client, user):
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(user).access_token}")


@pytest.mark.parametrize(
    "route,expected_fragment",
    [
        ("/admin/products", "planilha modelo"),
        ("/admin/settings?section=integrations&tab=pix", "Pix/subconta"),
        ("/admin/settings?section=integrations", "QR Code"),
        ("/admin/chat-logs", "Histórico de Chamados"),
        ("/admin/sales", "Painel de Vendas"),
        ("/admin/residents", "Moradores"),
        ("/admin/chatbot-flows", "Fluxos"),
        ("/admin/settings?section=markets", "Mercados"),
        ("/admin/settings?tab=plan", "Plano e pagamento"),
        ("/admin", "Dashboard"),
        ("/admin/", "Dashboard"),
        ("/admin/unknown-page", "assistente geral"),
    ],
)
def test_resolve_route_context(route, expected_fragment):
    ctx = resolve_route_context(route)
    assert expected_fragment.lower() in ctx.lower()


def test_resolve_route_context_pix_before_whatsapp():
    pix = resolve_route_context("/admin/settings?section=integrations&tab=pix")
    wa = resolve_route_context("/admin/settings?section=integrations")
    assert "Pix" in pix or "pix" in pix.lower()
    assert "QR Code" in wa


@pytest.mark.django_db
def test_support_chat_success(api_client, settings):
    settings.OPENAI_API_KEY = "test-key"
    user = UserFactory(email="copilot@example.com")
    _auth(api_client, user)

    with mock.patch("apps.support.services.copilot._get_client") as mock_get:
        mock_client = mock.Mock()
        mock_get.return_value = mock_client
        mock_client.chat.completions.create.return_value = mock.Mock(
            choices=[mock.Mock(message=mock.Mock(content="Resposta do copilot."))]
        )
        response = api_client.post(
            reverse("support-chat"),
            {
                "message": "Como conectar o WhatsApp?",
                "current_route": "/admin/settings?section=integrations",
                "chat_history": [{"role": "user", "content": "Oi"}],
            },
            format="json",
        )

    assert response.status_code == 200
    assert response.json()["reply"] == "Resposta do copilot."
    mock_client.chat.completions.create.assert_called_once()
    call_kwargs = mock_client.chat.completions.create.call_args.kwargs
    assert call_kwargs["temperature"] == 0.3
    messages = call_kwargs["messages"]
    assert messages[0]["role"] == "system"
    assert "QR Code" in messages[0]["content"]
    assert messages[-1]["role"] == "user"
    assert messages[-1]["content"] == "Como conectar o WhatsApp?"


@pytest.mark.django_db
def test_support_chat_missing_api_key_returns_503(api_client, settings):
    settings.OPENAI_API_KEY = ""
    user = UserFactory(email="copilot-nokey@example.com")
    _auth(api_client, user)

    response = api_client.post(
        reverse("support-chat"),
        {"message": "Olá", "current_route": "/admin"},
        format="json",
    )
    assert response.status_code == 503
    assert "não configurado" in response.json()["detail"].lower()


@pytest.mark.django_db
def test_support_chat_validation_error(api_client):
    user = UserFactory(email="copilot-bad@example.com")
    _auth(api_client, user)

    response = api_client.post(
        reverse("support-chat"),
        {"message": "", "current_route": "/admin"},
        format="json",
    )
    assert response.status_code == 400


@pytest.mark.django_db
def test_support_chat_openai_failure_returns_502(api_client, settings):
    settings.OPENAI_API_KEY = "test-key"
    user = UserFactory(email="copilot-fail@example.com")
    _auth(api_client, user)

    with mock.patch("apps.support.services.copilot._get_client") as mock_get:
        mock_client = mock.Mock()
        mock_get.return_value = mock_client
        mock_client.chat.completions.create.side_effect = RuntimeError("boom")
        response = api_client.post(
            reverse("support-chat"),
            {"message": "Ajuda", "current_route": "/admin/products"},
            format="json",
        )

    assert response.status_code == 502


def test_complete_support_chat_empty_message():
    with pytest.raises(SupportCopilotError, match="vazia"):
        complete_support_chat(message="  ", current_route="/admin")

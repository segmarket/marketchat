from unittest import mock

import pytest
from django.contrib.admin.sites import AdminSite

from apps.chatbot.admin import AIConfigurationAdmin
from apps.chatbot.defaults import (
    DEFAULT_ONBOARDING_MODEL,
    DEFAULT_ONBOARDING_SYSTEM_PROMPT,
    DEFAULT_ONBOARDING_TEMPERATURE,
)
from apps.chatbot.models import AIConfiguration
from apps.residents.services.onboarding_ai import analyze_onboarding_message


@pytest.mark.django_db
def test_get_active_config_returns_unsaved_defaults_when_empty():
    AIConfiguration.objects.all().delete()
    cfg = AIConfiguration.get_active_config()
    assert cfg.pk is None
    assert cfg.model_name == DEFAULT_ONBOARDING_MODEL
    assert cfg.temperature == DEFAULT_ONBOARDING_TEMPERATURE
    assert "intencao_primaria" in cfg.system_prompt
    assert cfg.system_prompt == DEFAULT_ONBOARDING_SYSTEM_PROMPT


@pytest.mark.django_db
def test_get_active_config_returns_active_row():
    AIConfiguration.objects.all().delete()
    active = AIConfiguration.objects.create(
        name="Custom",
        is_active=True,
        model_name="gpt-4o",
        temperature=0.1,
        system_prompt="PROMPT CUSTOMIZADO PARA TESTE",
    )
    AIConfiguration.objects.create(
        name="Old",
        is_active=False,
        model_name="gpt-4o-mini",
        temperature=0.5,
        system_prompt="outro",
    )
    cfg = AIConfiguration.get_active_config()
    assert cfg.pk == active.pk
    assert cfg.system_prompt == "PROMPT CUSTOMIZADO PARA TESTE"
    assert cfg.model_name == "gpt-4o"


@pytest.mark.django_db
def test_admin_save_keeps_single_active_configuration():
    AIConfiguration.objects.all().delete()
    first = AIConfiguration.objects.create(
        name="First",
        is_active=True,
        system_prompt="a",
    )
    second = AIConfiguration(
        name="Second",
        is_active=True,
        system_prompt="b",
    )
    admin = AIConfigurationAdmin(AIConfiguration, AdminSite())
    admin.save_model(request=mock.Mock(), obj=second, form=mock.Mock(), change=False)

    first.refresh_from_db()
    second.refresh_from_db()
    assert second.is_active is True
    assert first.is_active is False
    assert AIConfiguration.objects.filter(is_active=True).count() == 1


@pytest.mark.django_db
def test_analyze_onboarding_uses_active_ai_configuration():
    AIConfiguration.objects.all().delete()
    AIConfiguration.objects.create(
        name="Live",
        is_active=True,
        model_name="gpt-test-model",
        temperature=0.15,
        system_prompt="SYSTEM PROMPT FROM DB",
    )

    fake_response = mock.Mock()
    fake_response.choices = [
        mock.Mock(
            message=mock.Mock(
                content=(
                    '{"nome": null, "condominio": null, '
                    '"intencao_primaria": "cadastro_simples", '
                    '"acao_imediata_codigo": "continuar_onboarding", '
                    '"resposta_texto": "Qual o seu nome?"}'
                )
            )
        )
    ]
    fake_client = mock.Mock()
    fake_client.chat.completions.create.return_value = fake_response

    with (
        mock.patch(
            "apps.residents.services.onboarding_ai.settings.OPENAI_API_KEY",
            "sk-test",
        ),
        mock.patch(
            "apps.chatbot.services.chatbot_core._get_client",
            return_value=fake_client,
        ),
    ):
        result = analyze_onboarding_message("oi")

    assert result is not None
    assert result.resposta_texto == "Qual o seu nome?"
    kwargs = fake_client.chat.completions.create.call_args.kwargs
    assert kwargs["model"] == "gpt-test-model"
    assert kwargs["temperature"] == 0.15
    assert kwargs["messages"][0]["content"] == "SYSTEM PROMPT FROM DB"

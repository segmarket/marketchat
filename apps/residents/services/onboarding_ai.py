"""Análise de mensagens de onboarding via OpenAI (JSON — Porteiro Inteligente)."""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from typing import Any, Literal

from django.conf import settings

from apps.chatbot.defaults import (
    DEFAULT_ONBOARDING_MODEL,
    DEFAULT_ONBOARDING_SYSTEM_PROMPT,
    DEFAULT_ONBOARDING_TEMPERATURE,
)

logger = logging.getLogger(__name__)

VALID_INTENCOES_PRIMARIAS = frozenset(
    {
        "cadastro_simples",
        "reclamacao",
        "duvida",
        "vendas_spam",
        "transcricao_audio",
        "humano_urgente",
        "compra",
        "problema_maquininha",
    }
)
VALID_ACOES = frozenset(
    {
        "ignorar_mensagem",
        "pausar_bot_transferir",
        "iniciar_venda_backup",
        "continuar_onboarding",
    }
)
# Intents que não devem ir para pending_intent / resume pós-cadastro
NON_CACHEABLE_INTENTS = frozenset(
    {"vendas_spam", "transcricao_audio", "humano_urgente"}
)

DEFAULT_TRANSFER_MESSAGE = (
    "Entendi que você precisa de um atendimento mais detalhado. "
    "Vou pausar o assistente virtual e transferir para a nossa equipe humana. "
    "Aguarde um instante!"
)

ONBOARDING_AI_SOFT_FALLBACK_TEXT = (
    "Desculpe, nosso sistema cognitivo está passando por uma instabilidade "
    "momentânea. Qual era mesmo a sua solicitação?"
)

MissingField = Literal["nome", "condominio", "ambos", "nenhum"]

# Compat: constante usada em testes / imports externos
ONBOARDING_AI_SYSTEM_PROMPT = DEFAULT_ONBOARDING_SYSTEM_PROMPT


@dataclass(frozen=True)
class OnboardingAIResult:
    nome: str | None
    condominio: str | None
    intencao_primaria: str
    acao_imediata_codigo: str
    resposta_texto: str


def soft_fallback_onboarding_result() -> OnboardingAIResult:
    """JSON simulado seguro para a FSM não quebrar quando a OpenAI falha."""
    return OnboardingAIResult(
        nome=None,
        condominio=None,
        intencao_primaria="duvida",
        acao_imediata_codigo="continuar_onboarding",
        resposta_texto=ONBOARDING_AI_SOFT_FALLBACK_TEXT,
    )


def _strip_accents_alnum(value: str) -> str:
    raw = str(value or "").strip().lower()
    raw = (
        raw.replace("ã", "a")
        .replace("á", "a")
        .replace("â", "a")
        .replace("é", "e")
        .replace("ê", "e")
        .replace("í", "i")
        .replace("ó", "o")
        .replace("ô", "o")
        .replace("ú", "u")
        .replace("ç", "c")
    )
    return re.sub(r"[^a-z_]", "", raw)


def _normalize_optional_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text or text.lower() in {"null", "none", "n/a", "-"}:
        return None
    return text


def _normalize_intencao_primaria(value: Any) -> str:
    raw = _strip_accents_alnum(str(value or ""))
    # aliases legados
    if raw == "cadastro":
        raw = "cadastro_simples"
    if raw in VALID_INTENCOES_PRIMARIAS:
        return raw
    if "spam" in raw or "venda" in raw:
        return "vendas_spam"
    if "transcri" in raw or "audio" in raw:
        return "transcricao_audio"
    if "humano" in raw or "urgente" in raw or "atendente" in raw:
        return "humano_urgente"
    if "reclama" in raw:
        return "reclamacao"
    if "maquininha" in raw or "maquina" in raw or "totem" in raw:
        return "problema_maquininha"
    if "duvid" in raw:
        return "duvida"
    if "compra" in raw:
        return "compra"
    return "cadastro_simples"


def _normalize_acao(value: Any, *, intencao: str) -> str:
    raw = _strip_accents_alnum(str(value or ""))
    if raw in VALID_ACOES:
        return raw
    # Inferir pela intenção se a IA omitiu/errou a ação
    if intencao == "vendas_spam":
        return "ignorar_mensagem"
    if intencao in {"transcricao_audio", "humano_urgente"}:
        return "pausar_bot_transferir"
    if intencao == "problema_maquininha":
        return "iniciar_venda_backup"
    return "continuar_onboarding"


def _parse_payload(payload: dict[str, Any]) -> OnboardingAIResult | None:
    # Compat: chave antiga "intencao"
    intent_raw = payload.get("intencao_primaria", payload.get("intencao"))
    intencao = _normalize_intencao_primaria(intent_raw)
    acao = _normalize_acao(payload.get("acao_imediata_codigo"), intencao=intencao)

    nome = _normalize_optional_str(payload.get("nome"))
    condominio = _normalize_optional_str(payload.get("condominio"))

    raw_resposta = payload.get("resposta_texto")
    if raw_resposta is None:
        resposta = ""
    else:
        resposta = str(raw_resposta).strip()
        if resposta.lower() in {"null", "none", "n/a"}:
            resposta = ""

    if acao in {"ignorar_mensagem", "iniciar_venda_backup"}:
        resposta = ""
    elif acao == "pausar_bot_transferir":
        if not resposta:
            resposta = DEFAULT_TRANSFER_MESSAGE
    elif acao == "continuar_onboarding":
        # Vazio só é válido quando nome e condomínio já vieram (complete no mesmo turn)
        if not resposta and not (nome and condominio):
            return None

    return OnboardingAIResult(
        nome=nome,
        condominio=condominio,
        intencao_primaria=intencao,
        acao_imediata_codigo=acao,
        resposta_texto=resposta,
    )


def analyze_onboarding_message(
    user_text: str,
    *,
    known_name: str | None = None,
    known_condo: str | None = None,
    missing: MissingField = "ambos",
) -> OnboardingAIResult | None:
    """
    Extrai nome/condomínio/intenção/ação e gera resposta empática.
    Em falha de rede/API/JSON: retorna soft-fallback (continuar_onboarding).
    Retorna None só para texto vazio.
    """
    stripped = (user_text or "").strip()
    if not stripped:
        return None

    api_key = (settings.OPENAI_API_KEY or "").strip()
    if not api_key:
        logger.error(
            "onboarding_ai: OPENAI_API_KEY ausente; soft-fallback msg=%r",
            stripped[:80],
        )
        return soft_fallback_onboarding_result()

    from apps.chatbot.models import AIConfiguration

    config = AIConfiguration.get_active_config()
    system_prompt = (config.system_prompt or "").strip() or DEFAULT_ONBOARDING_SYSTEM_PROMPT
    model_name = (config.model_name or "").strip() or DEFAULT_ONBOARDING_MODEL
    try:
        temperature = float(config.temperature)
    except (TypeError, ValueError):
        temperature = DEFAULT_ONBOARDING_TEMPERATURE

    context_lines = [
        f"faltando: {missing}",
        f"nome_ja_conhecido: {known_name or 'null'}",
        f"condominio_ja_conhecido: {known_condo or 'null'}",
        f"Mensagem do morador:\n{stripped}",
    ]

    try:
        from apps.chatbot.services.chatbot_core import _get_client

        client = _get_client()
        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": "\n".join(context_lines)},
            ],
            response_format={"type": "json_object"},
            temperature=temperature,
        )
        raw = (response.choices[0].message.content or "").strip()
        payload = json.loads(raw)
        if not isinstance(payload, dict):
            logger.error(
                "onboarding_ai: payload não-dict; soft-fallback msg=%r",
                stripped[:80],
            )
            return soft_fallback_onboarding_result()
        parsed = _parse_payload(payload)
        if parsed is None:
            logger.error(
                "onboarding_ai: JSON inválido para FSM; soft-fallback msg=%r",
                stripped[:80],
            )
            return soft_fallback_onboarding_result()
        return parsed
    except Exception:
        logger.error(
            "onboarding_ai: falha ao analisar mensagem de onboarding msg=%r",
            stripped[:80],
            exc_info=True,
        )
        return soft_fallback_onboarding_result()


def analyze_onboarding_first_message(user_text: str) -> OnboardingAIResult | None:
    return analyze_onboarding_message(user_text, missing="ambos")

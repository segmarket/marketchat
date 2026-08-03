"""Classificação de intenção via IA (API externa)."""

from __future__ import annotations

import json
import logging
from typing import Any

from django.conf import settings

logger = logging.getLogger(__name__)

_JSON_SYSTEM_SUFFIX = (
    " You must respond strictly in JSON format containing the classified intent."
)

_GREETING_CLASSIFICATION_RULE = (
    "Se o usuário estiver iniciando a conversa ou enviando apenas saudações casuais "
    "(Ex: 'Bom dia', 'Boa tarde', 'Oi', 'Olá', 'Opa', 'Eae'), classifique estritamente como GREETING."
)

_COURTESY_CLASSIFICATION_RULE = (
    "Se o usuário estiver agradecendo por uma ação já concluída ou se despedindo para sair do chat "
    "(Ex: 'Obrigado', 'Valeu', 'Tchau', 'Fui', 'Certo, obrigado'), classifique estritamente como "
    "COURTESY_FAREWELL. 'Bom dia' ou 'Boa noite' como primeira mensagem do dia devem ser GREETING, "
    "não farewell."
)

_PRODUCT_SEARCH_CLASSIFICATION_RULE = (
    "REGRA DE CLASSIFICAÇÃO DE PRODUTOS SOLTOS: "
    "Se o usuário enviar apenas o nome de um produto (Ex: 'Cocada', 'Doritos', 'Água', 'Cerveja') "
    "ou perguntar sobre ele ('Tem cocada?'), a intenção é ESTRITAMENTE DE COMPRA ou BUSCA "
    "(PRODUCT_SEARCH / PURCHASE). "
    "NUNCA classifique como falta/ruptura de estoque (ALERTA_ESTOQUE / STOCK_ISSUE) a menos que "
    "o usuário use explicitamente palavras de ausência, como: 'acabou', 'faltando', 'não tem', "
    "'prateleira vazia', 'zerou'."
)


class IntentClassifierError(Exception):
    pass


def _build_system_prompt(system_prompt: str) -> str:
    base = system_prompt.strip() or (
        "Você classifica a intenção de mensagens de moradores de condomínio. "
        f"{_PRODUCT_SEARCH_CLASSIFICATION_RULE} "
        'Responda apenas com JSON no formato {"intent": "<uma das intenções>"}.'
    )
    if "greeting" not in base.lower() and "saudação" not in base.lower():
        base = f"{base.rstrip()} {_GREETING_CLASSIFICATION_RULE}"
    if "courtesy_farewell" not in base.lower() and "encerramento" not in base.lower():
        base = f"{base.rstrip()} {_COURTESY_CLASSIFICATION_RULE}"
    if "produtos soltos" not in base.lower() and "product_search" not in base.lower():
        base = f"{base.rstrip()} {_PRODUCT_SEARCH_CLASSIFICATION_RULE}"
    if "json" not in base.lower():
        base = f"{base.rstrip()}{_JSON_SYSTEM_SUFFIX}"
    return base


def _gatekeeper_messages(
    *,
    system_prompt: str,
    history: list[dict[str, str]],
    current_user_message: str,
) -> list[dict[str, str]]:
    """Evita duplicar a mensagem atual se já foi gravada no Redis antes da classificação."""
    stripped = current_user_message.strip()
    if (
        history
        and history[-1].get("role") == "user"
        and history[-1].get("content", "").strip() == stripped
    ):
        return [{"role": "system", "content": system_prompt.strip()}] + [
            {"role": h["role"], "content": h["content"]} for h in history
        ]

    from apps.chatbot.services.chat_context_cache import build_openai_messages

    return build_openai_messages(
        system_prompt=system_prompt,
        history=history,
        current_user_message=stripped,
    )


def classify_gatekeeper_intent(
    *,
    message: str,
    tenant_id: int,
    phone: str,
) -> str:
    """
    Classifica intenção do gatekeeper com histórico recente no Redis.
    Retorna tag em maiúsculas (PURCHASE, COURTESY_FAREWELL, etc.).
    """
    from apps.chatbot.services.chatbot_core import (
        GATEKEEPER_STATIC_SYSTEM,
        parse_gatekeeper_tag,
    )
    from apps.chatbot.services.chat_context_cache import get_recent_messages

    stripped = (message or "").strip()
    if not stripped:
        return "GENERAL"

    api_key = (settings.OPENAI_API_KEY or "").strip()
    if not api_key:
        logger.warning("Gatekeeper: OPENAI_API_KEY ausente; usando GENERAL")
        return "GENERAL"

    history = get_recent_messages(tenant_id, phone)
    messages = _gatekeeper_messages(
        system_prompt=GATEKEEPER_STATIC_SYSTEM,
        history=history,
        current_user_message=stripped,
    )

    try:
        from openai import BadRequestError, OpenAI

        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=messages,
            max_tokens=16,
            temperature=0,
        )
        raw = (response.choices[0].message.content or "").strip()
        return parse_gatekeeper_tag(raw)
    except BadRequestError as exc:
        logger.warning("Gatekeeper OpenAI BadRequest: %s; fallback isolado", exc)
    except Exception:
        logger.warning("Gatekeeper: falha com contexto; fallback isolado", exc_info=True)

    return classify_gatekeeper_intent_isolated(message=stripped)


def classify_gatekeeper_intent_isolated(*, message: str) -> str:
    """Classificação sem histórico (degradação graceful)."""
    from apps.chatbot.services.chatbot_core import (
        GATEKEEPER_STATIC_SYSTEM,
        ChatbotCoreError,
        complete_plain,
        parse_gatekeeper_tag,
    )

    try:
        raw = complete_plain(
            static_system=GATEKEEPER_STATIC_SYSTEM,
            user_content=message,
            max_tokens=16,
            temperature=0,
            apply_conciseness_rule=False,
        )
        return parse_gatekeeper_tag(raw)
    except ChatbotCoreError:
        return "GENERAL"
    except Exception:
        logger.exception("Gatekeeper isolado: falha na classificação")
        return "GENERAL"


def classify_intent(*, message: str, intents: list[str], system_prompt: str = "") -> str:
    """
    Retorna a intent escolhida (string) dentre a lista fornecida.
    """
    cleaned_intents = [i.strip() for i in intents if i and i.strip()]
    if not cleaned_intents:
        raise IntentClassifierError("Lista de intenções vazia.")

    stripped_message = (message or "").strip()
    if not stripped_message:
        fallback = cleaned_intents[0]
        logger.info("classify_intent: mensagem vazia; fallback=%s", fallback)
        return fallback

    api_key = (settings.OPENAI_API_KEY or "").strip()
    if not api_key:
        raise IntentClassifierError("Serviço de IA não configurado.")

    from openai import OpenAI

    client = OpenAI(api_key=api_key)
    model = settings.OPENAI_MODEL

    user_content = (
        f"Mensagem do morador:\n{stripped_message}\n\n"
        f"Intenções possíveis (escolha exatamente uma): {json.dumps(cleaned_intents, ensure_ascii=False)}"
    )
    system = _build_system_prompt(system_prompt)
    fallback_intent = cleaned_intents[0]

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user_content},
            ],
            response_format={"type": "json_object"},
            temperature=0.2,
        )
    except Exception as exc:
        from openai import BadRequestError

        if isinstance(exc, BadRequestError):
            logger.warning(
                "OpenAI BadRequest na classificação de intenção: %s; fallback=%s",
                exc,
                fallback_intent,
            )
            return fallback_intent
        logger.exception("Falha na API de IA")
        raise IntentClassifierError("Falha ao classificar intenção.") from exc

    raw = (response.choices[0].message.content or "").strip()
    try:
        payload: dict[str, Any] = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise IntentClassifierError("Resposta da IA inválida.") from exc

    intent = str(payload.get("intent") or "").strip()
    if intent not in cleaned_intents:
        lowered = intent.lower()
        for candidate in cleaned_intents:
            if candidate.lower() == lowered:
                return candidate
        raise IntentClassifierError(f"Intenção fora da lista: {intent!r}")
    return intent

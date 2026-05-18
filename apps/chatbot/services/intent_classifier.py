"""Classificação de intenção via IA (API externa)."""

from __future__ import annotations

import json
import logging
from typing import Any

from django.conf import settings

logger = logging.getLogger(__name__)


class IntentClassifierError(Exception):
    pass


def classify_intent(*, message: str, intents: list[str], system_prompt: str = "") -> str:
    """
    Retorna a intent escolhida (string) dentre a lista fornecida.
    """
    cleaned_intents = [i.strip() for i in intents if i and i.strip()]
    if not cleaned_intents:
        raise IntentClassifierError("Lista de intenções vazia.")

    api_key = (settings.OPENAI_API_KEY or "").strip()
    if not api_key:
        raise IntentClassifierError("Serviço de IA não configurado.")

    from openai import OpenAI

    client = OpenAI(api_key=api_key)
    model = settings.OPENAI_MODEL

    user_content = (
        f"Mensagem do morador:\n{message.strip()}\n\n"
        f"Intenções possíveis (escolha exatamente uma): {json.dumps(cleaned_intents, ensure_ascii=False)}"
    )
    system = system_prompt.strip() or (
        "Você classifica a intenção de mensagens de moradores de condomínio. "
        "Responda apenas com JSON no formato {\"intent\": \"<uma das intenções>\"}."
    )

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

"""Núcleo OpenAI: prompts cacheáveis, histórico limitado e triagem enxuta."""

from __future__ import annotations

import logging
import re

from django.conf import settings

from apps.chatbot.services.chat_history import (
    append_assistant_message,
    append_user_message,
    get_sliding_history,
)
from apps.residents.models import ChatSession

logger = logging.getLogger(__name__)

GOLDEN_RULE_CONCISENESS = (
    "⚠️ REGRA DE OURO: Seja extremamente direto, curto e amigável. "
    "Suas respostas devem ter no máximo 2 frases. Nunca use enrolação ou textos longos."
)

# Blocos estáticos (prefixo idêntico entre requisições — prompt caching OpenAI).
STATIC_GENERAL_ASSISTANT = (
    "Você é o assistente virtual amigável de um mercado autônomo de condomínio. "
    "Responda em português do Brasil, de forma breve e clara, adequada para leitura no celular. "
    "Seja acolhedor e objetivo."
)

STATIC_STOCK_ASSISTANT = (
    "Você é o assistente de estoque de um mercado autônomo de condomínio. "
    "Com base nos dados do catálogo fornecidos na mensagem do usuário, informe se o produto "
    "está disponível, em falta ou se a reposição costuma ocorrer em breve. "
    "Se não houver informação suficiente, diga que vai verificar com a equipe."
)

STATIC_PRODUCT_EXTRACTOR = (
    "Extraia apenas o nome do produto ou marca que o usuário deseja comprar. "
    "Responda estritamente com o termo extraído, sem pontuações ou saudações. "
    "Se o usuário disser que quer comprar, mas não especificar nenhuma marca ou produto "
    "na frase (ex: 'quero comprar', 'quero ver produtos'), responda estritamente e "
    "apenas com a palavra: NONE"
)

GATEKEEPER_STATIC_SYSTEM = (
    "Você é um classificador de intenções estrito para um chatbot de mercado autônomo em condomínio.\n"
    "Sua única tarefa é responder com uma das seguintes tags: PURCHASE, MAINTENANCE_ISSUE, "
    "COMPLAINT, PAYMENT_ERROR, STOCK_ISSUE, ou GENERAL.\n\n"
    "⚠️ REGRA DE PRIORIDADE MÁXIMA:\n"
    "Se o usuário mencionar que um produto ACABOU, ESTÁ EM FALTA, NÃO TEM na gôndola/geladeira "
    "ou que ele QUERIA COMPRAR MAS NÃO ACHOU, a intenção OBRIGATORIAMENTE é STOCK_ISSUE. "
    "O relato de falta de produto anula a intenção de compra.\n\n"
    "Exemplos de Treinamento:\n"
    "- 'Quero comprar uma coca cola e um ruffles' -> PURCHASE\n"
    "- 'Vou levar um chocolate' -> PURCHASE\n"
    "- 'Queria comprar o Magnum mas está em falta' -> STOCK_ISSUE\n"
    "- 'O freezer de sorvete tá vazio, não tem mais nada' -> STOCK_ISSUE\n"
    "- 'Quando vai chegar a coca de 2 litros?' -> STOCK_ISSUE\n"
    "- 'A maquininha de cartão tá sem sinal' -> PAYMENT_ERROR\n"
    "- 'Problema para finalizar o pagamento' -> PAYMENT_ERROR\n"
    "- 'A lâmpada do mercado queimou' -> MAINTENANCE_ISSUE\n"
    "- 'Quero fazer uma reclamação sobre o atendimento' -> COMPLAINT\n"
    "- 'Estou insatisfeito com a compra de ontem' -> COMPLAINT\n"
    "- 'Oi, boa noite' -> GENERAL\n\n"
    "Responda APENAS E STRICTAMENTE com a palavra-chave da tag em letras maiúsculas, "
    "sem pontuação, justificativas ou saudações."
)

GATEKEEPER_TAGS = frozenset(
    {
        "PURCHASE",
        "MAINTENANCE_ISSUE",
        "COMPLAINT",
        "PAYMENT_ERROR",
        "STOCK_ISSUE",
        "GENERAL",
    },
)

STATIC_COMPLAINT_ASSISTANT = (
    "Você é o assistente de atendimento de um mercado autônomo de condomínio. "
    "O morador está registrando uma RECLAMAÇÃO (insatisfação com produto, serviço, "
    "atendimento ou experiência no mercado). "
    "Ouça com empatia, peça desculpas pelo transtorno quando fizer sentido e "
    "convide-o a descrever o que aconteceu com calma. "
    "Não minimize o problema nem discuta. "
    "Se faltar detalhe, faça uma pergunta objetiva para entender melhor."
)


class ChatbotCoreError(Exception):
    pass


def build_system_prompt(
    *,
    static_instructions: str,
    dynamic_tail: str = "",
    apply_conciseness_rule: bool = True,
) -> str:
    """
    Monta system prompt com bloco estático primeiro (cacheável) e variáveis no final.
    """
    parts = [static_instructions.strip()]
    if apply_conciseness_rule:
        parts.append(GOLDEN_RULE_CONCISENESS)
    dynamic = (dynamic_tail or "").strip()
    if dynamic:
        parts.append(dynamic)
    return "\n\n".join(parts)


def _get_client():
    api_key = (settings.OPENAI_API_KEY or "").strip()
    if not api_key:
        raise ChatbotCoreError("Serviço de IA não configurado.")
    from openai import OpenAI

    return OpenAI(api_key=api_key)


def complete_plain(
    *,
    static_system: str,
    user_content: str,
    max_tokens: int = 120,
    temperature: float = 0.2,
    dynamic_system_tail: str = "",
    apply_conciseness_rule: bool = True,
) -> str:
    """Uma rodada sem histórico: system estático + user (dinâmico no final)."""
    system = build_system_prompt(
        static_instructions=static_system,
        dynamic_tail=dynamic_system_tail,
        apply_conciseness_rule=apply_conciseness_rule,
    )
    client = _get_client()
    response = client.chat.completions.create(
        model=settings.OPENAI_MODEL,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user_content.strip()},
        ],
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return (response.choices[0].message.content or "").strip()


def complete_with_session_history(
    *,
    session: ChatSession,
    static_system: str,
    user_content: str,
    dynamic_system_tail: str = "",
    max_tokens: int = 80,
    temperature: float = 0.4,
    record_user: bool = True,
    record_assistant: bool = True,
) -> str:
    """
    Conversa com janela deslizante: grava user, envia últimas N mensagens + user atual, grava assistant.
    """
    user_text = user_content.strip()
    if not user_text:
        raise ChatbotCoreError("Mensagem vazia.")

    if record_user:
        append_user_message(session, user_text)

    system = build_system_prompt(
        static_instructions=static_system,
        dynamic_tail=dynamic_system_tail,
    )

    history = get_sliding_history(session)
    # Garante que a mensagem atual do usuário seja a última do array.
    if not history or history[-1].get("role") != "user" or history[-1].get("content") != user_text:
        history = [m for m in history if not (m.get("role") == "user" and m.get("content") == user_text)]
        history.append({"role": "user", "content": user_text})

    messages: list[dict[str, str]] = [{"role": "system", "content": system}]
    messages.extend(history)

    client = _get_client()
    response = client.chat.completions.create(
        model=settings.OPENAI_MODEL,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    reply = (response.choices[0].message.content or "").strip()

    if record_assistant and reply:
        append_assistant_message(session, reply)

    return reply


def parse_gatekeeper_tag(raw: str) -> str:
    """Normaliza retorno em texto puro para uma tag válida."""
    cleaned = (raw or "").strip().upper()
    if not cleaned:
        return "GENERAL"
    token = re.sub(r"[^A-Z_]", "", cleaned.split()[0] if cleaned.split() else cleaned)
    if token in GATEKEEPER_TAGS:
        return token
    for tag in GATEKEEPER_TAGS:
        if tag in cleaned:
            return tag
    return "GENERAL"


def classify_gatekeeper_intent(message: str) -> str:
    """Triagem sem JSON e sem histórico (mínimo de tokens)."""
    stripped = (message or "").strip()
    if not stripped:
        return "GENERAL"
    try:
        raw = complete_plain(
            static_system=GATEKEEPER_STATIC_SYSTEM,
            user_content=stripped,
            max_tokens=12,
            temperature=0,
            apply_conciseness_rule=False,
        )
    except ChatbotCoreError:
        logger.warning("Gatekeeper: IA indisponível; usando GENERAL")
        return "GENERAL"
    except Exception:
        logger.exception("Gatekeeper: falha na classificação")
        return "GENERAL"
    return parse_gatekeeper_tag(raw)


def extract_product_term(message: str) -> str:
    """Extração de termo de produto (uma rodada, sem histórico)."""
    stripped = (message or "").strip()
    if not stripped:
        raise ChatbotCoreError("Mensagem vazia.")
    try:
        term = complete_plain(
            static_system=STATIC_PRODUCT_EXTRACTOR,
            user_content=stripped,
            max_tokens=24,
            temperature=0,
        )
    except Exception as exc:
        logger.exception("Falha na extração de termo de produto")
        raise ChatbotCoreError("Falha ao processar sua mensagem.") from exc
    if not term:
        raise ChatbotCoreError("Não foi possível identificar o produto.")
    from apps.sales.services.product_search import normalize_extracted_term

    return normalize_extracted_term(term)

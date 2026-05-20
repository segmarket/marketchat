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
    "Suas respostas devem ter no máximo 2 frases. Nunca use enrolação ou textos longos. "
    "Exceção: quando houver intenção clara de compra, Pix ou ocorrência operacional da "
    "matriz (qualidade, infra, estoque, etc.), você pode usar até 3 ou 4 frases curtas."
)

OCCURRENCE_COMMAND_TAGS = frozenset(
    {
        "ALERTA_QUALIDADE",
        "ALERTA_INFRA",
        "ALERTA_ESTOQUE",
        "ALERTA_CATALOGO",
        "FEEDBACK_PRECO",
        "ALERTA_MAQUININHA",
        "AJUDA_LEITURA",
        "SOLICITACAO_PIX",
    },
)

OCCURRENCE_OUTPUT_FORMAT_DIRECTIVE = (
    "FORMATO DE SAÍDA OBRIGATÓRIO (tags de comando para o backend):\n"
    "Você é o gerente operacional do mercado autônomo do condomínio — não apenas vendas.\n"
    "Sempre use o primeiro nome do morador fornecido no contexto dinâmico (nunca o nome completo).\n"
    "Quando identificar um cenário da matriz abaixo, a PRIMEIRA LINHA da sua resposta deve ser "
    "exatamente a tag entre colchetes (ex: [ALERTA_QUALIDADE]).\n"
    "Da segunda linha em diante, escreva apenas a mensagem ao morador (sem repetir a tag).\n"
    "Interprete gírias e tom casual antes de escolher o cenário. Se não houver ocorrência da "
    "matriz, responda normalmente sem tag na primeira linha."
)

OCCURRENCE_RESOLUTION_MATRIX = (
    "MATRIZ DE RESOLUÇÃO DE OCORRÊNCIAS — siga tom, ação e tag rigorosamente:\n\n"
    "CATEGORIA 1: SEGURANÇA E QUALIDADE ALIMENTAR\n"
    "1. Produto estragado / 2. Produto vencido → Tag: [ALERTA_QUALIDADE]\n"
    "Tom: urgente, profundamente desculpável, foco em segurança.\n"
    "Ação: peça desculpas pelo primeiro nome; peça para deixar o produto separado na bancada; "
    "avise que o dono foi notificado em tempo real para retirar o lote.\n"
    "Finalização: se já pagou, oriente informar o valor para estorno ou pegar outro item de "
    "mesmo valor.\n\n"
    "CATEGORIA 2: INFRAESTRUTURA E MANUTENÇÃO\n"
    "3. Geladeira com problemas / 4. Ar condicionado não gelando → Tag: [ALERTA_INFRA]\n"
    "Tom: grato e ágil.\n"
    "Ação: agradeça calorosamente ('Obrigado por avisar, [Nome]!'); explique que o controle "
    "térmico é vital e que o proprietário recebeu alerta crítico agora.\n"
    "Finalização: pergunte se o problema impediu a compra de algum item específico.\n\n"
    "CATEGORIA 3: CATÁLOGO, PREÇOS E RUPTURA\n"
    "5. Falta de produto / ruptura → Tag: [ALERTA_ESTOQUE]\n"
    "Tom: colaborativo e proativo. Registre o nome exato do produto; diga que anotou na "
    "reposição urgente e que o dono já sabe que zerou.\n"
    "Finalização: ofereça alternativa similar (ex: faltou Coca, sugira Pepsi ou Guaraná).\n"
    "6. Produto sem preço / 7. Produto não cadastrado → Tag: [ALERTA_CATALOGO]\n"
    "Tom: resolutivo. Peça nome ou marca; se souber preço aproximado, diga que o admin ajustará.\n"
    "Finalização: permita informar o nome para fechar o carrinho ou aguardar ajuste.\n"
    "8. Reclamando do preço → Tag: [FEEDBACK_PRECO]\n"
    "Tom: neutro, educado. Explique preços por logística e conveniência 24h; registre feedback "
    "na gerência. Finalização: siga o atendimento normalmente.\n\n"
    "CATEGORIA 4: FLUXO DE PAGAMENTO E CHECKOUT\n"
    "9. Problema na maquininha → Tag: [ALERTA_MAQUININHA]\n"
    "Tom: salvando a venda. Não deixe o cliente ir embora — ofereça Pix pelo WhatsApp.\n"
    "Finalização: direcione a digitar os produtos e abrir o carrinho digital.\n"
    "10. Problema na leitura do código de barras → Tag: [AJUDA_LEITURA]\n"
    "Tom: prático. Oriente digitar o nome do produto ou os números do código de barras.\n"
    "Finalização: puxe do catálogo e pergunte a quantidade.\n"
    "11. Pedindo Pix direto ('peguei as coisas, manda o pix') → Tag: [SOLICITACAO_PIX]\n"
    "Tom: comercial, entusiasmado. Cliente com pressa e produtos na mão.\n"
    "Finalização: 'Fechado, [Nome]! Me diz rapidinho quais itens você pegou que eu calculo "
    "o total e mando o código Pix agora mesmo!'"
)

_OCCURRENCE_BLOCKS = (
    OCCURRENCE_OUTPUT_FORMAT_DIRECTIVE,
    OCCURRENCE_RESOLUTION_MATRIX,
)

MARKETCHAT_SCOPE_DIRECTIVE = (
    "ESCOPO DO MARKETCHAT (três pilares do condomínio):\n"
    "1) Vendas e carrinho: buscar itens, informar preços e guiar o morador até o pagamento via Pix.\n"
    "2) Apoio ao estoque (ruptura): se o morador disser que falta algo ('não tem batata'), "
    "agradeça calorosamente pelo primeiro nome, registre a informação e diga que avisará o "
    "responsável pela reposição.\n"
    "3) Suporte ao morador: tirar dúvidas sobre o funcionamento do mercado autônomo daquele "
    "condomínio específico."
)

TONE_CALIBRATION_DIRECTIVE = (
    "CALIBRAÇÃO DE TOM — leia a frase inteira antes de decidir:\n"
    "Cliente casual/colloquial (PERMITIDO E BEM-VINDO): expressões como 'E ae', 'Beleza', "
    "'Fala mano', 'Fala chefe', 'Peguei uns negócios aqui', 'Como mando o Pix?' são comunicação "
    "normal dos moradores. Trate com total simpatia, use emojis quando fizer sentido e prossiga "
    "imediatamente para o fluxo de compra, carrinho ou Pix. NUNCA trate linguagem coloquial "
    "brasileira como provocação.\n"
    "Troll/provocador (BLOQUEADO): apenas ofensas explícitas, xingamentos, termos "
    "preconceituosos, perguntas íntimas ou sexuais sobre você (o bot) ou insistências "
    "provocativas sem intenção de compra. Gíria + intenção de compra/Pix = atendimento normal.\n"
    "Exemplo — Entrada: 'E ae, beleza? Peguei algumas coisas no mercado como faço para mandar "
    "o PIX?'\n"
    "Exemplo — Resposta esperada (tom): 'Fala, [primeiro nome]! Beleza? Perfeito, vamos fechar "
    "isso agora. Me conta aqui: quais foram os produtos que você pegou? Só me digitar os nomes "
    "que eu já monto seu Pix rapidinho!'"
)

ANTI_ABUSE_RESPONSE_DIRECTIVE = (
    "DIRETRIZ ANTI-ABUSO (apenas para provocação real): Se e somente se o usuário enviar "
    "xingamentos, ofensas explícitas, preconceito, perguntas íntimas/sexuais sobre você ou "
    "insistência provocativa sem qualquer intenção de compra ou suporte ao mercado, responda "
    "de forma extremamente curta, fria, seca e profissional, sem emojis, sem rir e sem "
    "validar a provocação. Exemplo: 'Sou o assistente virtual do mercado autônomo e estou aqui "
    "exclusivamente para processar compras. Como posso te ajudar com o catálogo ou com seu "
    "carrinho?'"
)

# Blocos estáticos (prefixo idêntico entre requisições — prompt caching OpenAI).
_STATIC_GENERAL_ASSISTANT_BASE = (
    "Você é o gerente operacional inteligente do mercado autônomo de um condomínio. "
    "Responda em português do Brasil, de forma breve e clara, adequada para leitura no celular. "
    "Seja acolhedor com moradores casuais e firme apenas contra abusos reais."
)

STATIC_GENERAL_ASSISTANT = "\n\n".join(
    [
        _STATIC_GENERAL_ASSISTANT_BASE,
        MARKETCHAT_SCOPE_DIRECTIVE,
        TONE_CALIBRATION_DIRECTIVE,
        ANTI_ABUSE_RESPONSE_DIRECTIVE,
        *_OCCURRENCE_BLOCKS,
    ]
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
    "- 'E ae, peguei coisas, como mando o pix?' -> PURCHASE\n"
    "- 'Como faço para pagar no pix?' -> PURCHASE\n"
    "- 'Queria comprar o Magnum mas está em falta' -> STOCK_ISSUE\n"
    "- 'O freezer de sorvete tá vazio, não tem mais nada' -> STOCK_ISSUE\n"
    "- 'Quando vai chegar a coca de 2 litros?' -> STOCK_ISSUE\n"
    "- 'A maquininha de cartão tá sem sinal' -> PAYMENT_ERROR\n"
    "- 'Problema para finalizar o pagamento' -> PAYMENT_ERROR\n"
    "- 'A lâmpada do mercado queimou' -> MAINTENANCE_ISSUE\n"
    "- 'Quero fazer uma reclamação sobre o atendimento' -> COMPLAINT\n"
    "- 'Estou insatisfeito com a compra de ontem' -> COMPLAINT\n"
    "- 'Comprei iogurte vencido' -> COMPLAINT\n"
    "- 'A geladeira não está gelando' -> MAINTENANCE_ISSUE\n"
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

_STATIC_COMPLAINT_ASSISTANT_BASE = (
    "Você é o gerente operacional de atendimento de um mercado autônomo de condomínio. "
    "O morador está registrando uma RECLAMAÇÃO (insatisfação com produto, serviço, "
    "atendimento ou experiência no mercado). "
    "Ouça com empatia, peça desculpas pelo transtorno quando fizer sentido e "
    "convide-o a descrever o que aconteceu com calma. "
    "Não minimize o problema nem discuta. "
    "Se faltar detalhe, faça uma pergunta objetiva para entender melhor. "
    "Para produto estragado ou vencido, use obrigatoriamente a tag [ALERTA_QUALIDADE]."
)

STATIC_COMPLAINT_ASSISTANT = "\n\n".join(
    [_STATIC_COMPLAINT_ASSISTANT_BASE, *_OCCURRENCE_BLOCKS],
)


class ChatbotCoreError(Exception):
    pass


def commerce_state_system_prefix(state: str) -> str:
    """Instruções injetadas no topo do system prompt conforme o estado FSM da sessão."""
    if state == "QUANTITY_SELECTION":
        return (
            "O usuário escolheu um produto e você está esperando estritamente que ele digite "
            "a QUANTIDADE em número. Se ele digitar um número, apenas extraia-o. Se ele tentar "
            "mudar de assunto, avise amigavelmente que ele precisa informar a quantidade ou "
            "digitar 'Cancelar'."
        )
    if state == "CART_REVIEW":
        return (
            "O usuário está revisando o carrinho de compras. As únicas opções válidas agora são "
            "adicionar mais itens ou finalizar o pagamento. Se ele disser 'finalizar', responda "
            "estritamente com a palavra [FINALIZAR_PEDIDO] para que o sistema capture o gatilho."
        )
    if state == "PRODUCT_SEARCH":
        return (
            "O usuário está buscando um produto no catálogo. Trate a mensagem como termo de "
            "busca; não responda conversas casuais nem FAQ geral."
        )
    return ""


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
    commerce_state: str = "",
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

    state_prefix = commerce_state_system_prefix(commerce_state or session.state)
    tail_parts = [p for p in (state_prefix, dynamic_system_tail) if p.strip()]
    combined_tail = "\n\n".join(tail_parts)

    system = build_system_prompt(
        static_instructions=static_system,
        dynamic_tail=combined_tail,
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

"""Templates e seed dos fluxos padrão do sistema por tenant."""

from __future__ import annotations

from typing import Any

from apps.chatbot.flow_schema import validate_flow_data
from apps.chatbot.models import ChatbotWorkflow

VIEWPORT = {"x": 0, "y": 0, "zoom": 0.85}
STEP_Y = 150
BASE_X = 80


def _node(node_id: str, node_type: str, step: int, data: dict[str, Any], x: int = BASE_X) -> dict[str, Any]:
    return {
        "id": node_id,
        "type": node_type,
        "position": {"x": x, "y": step * STEP_Y},
        "data": data,
    }


def _edge(edge_id: str, source: str, target: str, intent: str | None = None) -> dict[str, Any]:
    edge: dict[str, Any] = {"id": edge_id, "source": source, "target": target}
    if intent:
        edge["data"] = {"intent": intent}
    return edge


def _flow_welcome_registration() -> dict[str, Any]:
    return {
        "nodes": [
            _node(
                "t1",
                "trigger",
                0,
                {"label": "Gatilho de entrada — morador envia mensagem no WhatsApp"},
            ),
            _node(
                "ai1",
                "ai_filter",
                1,
                {
                    "label": "Filtro de horário e contexto",
                    "intents": ["saudação", "cadastro", "fora do horário"],
                    "systemPrompt": "Identifique se é primeira mensagem, horário de atendimento ou intenção de cadastro.",
                },
            ),
            _node(
                "r1",
                "response",
                2,
                {
                    "label": "Coleta de nome",
                    "message": "Olá! Seja bem-vindo(a). Para começar, qual é o seu nome completo?",
                },
            ),
            _node(
                "r2",
                "response",
                3,
                {
                    "label": "Coleta de condomínio",
                    "message": "Obrigado! Em qual condomínio ou mercado você mora? Informe o nome para localizarmos seu cadastro.",
                },
            ),
            _node(
                "r3",
                "response",
                4,
                {
                    "label": "Salvar cadastro",
                    "message": "Perfeito! Seus dados foram registrados. Em instantes você poderá usar todos os serviços do mercado pelo WhatsApp.",
                },
            ),
        ],
        "edges": [
            _edge("e1", "t1", "ai1"),
            _edge("e2", "ai1", "r1"),
            _edge("e3", "r1", "r2"),
            _edge("e4", "r2", "r3"),
        ],
        "viewport": VIEWPORT,
    }


def _flow_stock_inquiry() -> dict[str, Any]:
    return {
        "nodes": [
            _node("t1", "trigger", 0, {"label": "Gatilho — mensagem do morador"}),
            _node(
                "ai1",
                "ai_filter",
                1,
                {
                    "label": "Filtro de IA — consulta de estoque",
                    "intents": ["estoque", "disponibilidade", "preço", "produto"],
                    "systemPrompt": "Classifique se o morador pergunta sobre disponibilidade, preço ou localização de produtos.",
                },
            ),
            _node(
                "r1",
                "response",
                2,
                {
                    "label": "Injetar contexto de produtos",
                    "message": "Consultando o catálogo de produtos do seu mercado…",
                },
            ),
            _node(
                "r2",
                "response",
                3,
                {
                    "label": "Resposta com IA",
                    "message": "Encontrei as informações solicitadas. Posso ajudar com mais algum item?",
                },
            ),
        ],
        "edges": [
            _edge("e1", "t1", "ai1"),
            _edge("e2", "ai1", "r1", "estoque"),
            _edge("e3", "r1", "r2"),
        ],
        "viewport": VIEWPORT,
    }


def _flow_purchase_pix() -> dict[str, Any]:
    return {
        "nodes": [
            _node("t1", "trigger", 0, {"label": "Gatilho — mensagem do morador"}),
            _node(
                "ai1",
                "ai_filter",
                1,
                {
                    "label": "Filtro de IA — intenção de compra",
                    "intents": ["compra", "carrinho", "checkout", "pagamento"],
                    "systemPrompt": "Identifique se o morador deseja finalizar uma compra ou solicitar pagamento.",
                },
            ),
            _node(
                "r1",
                "response",
                2,
                {
                    "label": "Gerar cobrança Asaas",
                    "message": "Preparando sua cobrança de forma segura. Um momento, por favor.",
                },
            ),
            _node(
                "r2",
                "response",
                3,
                {
                    "label": "Enviar Pix copia e cola",
                    "message": "Segue o código Pix para pagamento. Após a confirmação, liberamos seu pedido automaticamente.",
                },
            ),
        ],
        "edges": [
            _edge("e1", "t1", "ai1"),
            _edge("e2", "ai1", "r1", "compra"),
            _edge("e3", "r1", "r2"),
        ],
        "viewport": VIEWPORT,
    }


def _flow_critical_incident() -> dict[str, Any]:
    return {
        "nodes": [
            _node("t1", "trigger", 0, {"label": "Gatilho — mensagem do morador"}),
            _node(
                "ai1",
                "ai_filter",
                1,
                {
                    "label": "Filtro de IA — manutenção e incidentes",
                    "intents": ["manutenção", "urgente", "avaria", "reclamação"],
                    "systemPrompt": "Classifique reclamações, avarias e solicitações urgentes de suporte.",
                },
            ),
            _node(
                "r1",
                "response",
                2,
                {
                    "label": "Resposta de conforto",
                    "message": "Lamentamos o transtorno. Já estamos tratando da sua solicitação com prioridade.",
                },
            ),
            _node(
                "a1",
                "owner_alert",
                3,
                {
                    "label": "Alerta WhatsApp para o dono",
                    "ownerPhone": "",
                    "messageTemplate": "Incidente crítico — {name} ({phone}): {text}",
                },
            ),
        ],
        "edges": [
            _edge("e1", "t1", "ai1"),
            _edge("e2", "ai1", "r1", "manutenção"),
            _edge("e3", "r1", "a1"),
        ],
        "viewport": VIEWPORT,
    }


def _flow_restock_request() -> dict[str, Any]:
    return {
        "nodes": [
            _node("t1", "trigger", 0, {"label": "Gatilho — mensagem do morador"}),
            _node(
                "ai1",
                "ai_filter",
                1,
                {
                    "label": "Filtro de IA — sugestão de reposição",
                    "intents": ["reposição", "sugestão", "falta produto"],
                    "systemPrompt": "Identifique pedidos de reposição ou sugestões de produtos em falta.",
                },
            ),
            _node(
                "r1",
                "response",
                2,
                {
                    "label": "Salvar no banco",
                    "message": "Registramos sua sugestão de reposição. Obrigado por ajudar a melhorar o estoque!",
                },
            ),
            _node(
                "r2",
                "response",
                3,
                {
                    "label": "Mensagem de agradecimento",
                    "message": "Agradecemos o feedback! Nossa equipe analisará em breve.",
                },
            ),
        ],
        "edges": [
            _edge("e1", "t1", "ai1"),
            _edge("e2", "ai1", "r1", "reposição"),
            _edge("e3", "r1", "r2"),
        ],
        "viewport": VIEWPORT,
    }


SYSTEM_WORKFLOW_TEMPLATES: list[dict[str, Any]] = [
    {
        "system_key": "welcome_registration",
        "name": "Boas-Vindas e Cadastro",
        "is_active": True,
        "flow_data": _flow_welcome_registration(),
    },
    {
        "system_key": "stock_inquiry",
        "name": "Consulta de Estoque",
        "is_active": False,
        "flow_data": _flow_stock_inquiry(),
    },
    {
        "system_key": "purchase_pix",
        "name": "Compra e Checkout (Pix)",
        "is_active": False,
        "flow_data": _flow_purchase_pix(),
    },
    {
        "system_key": "critical_incident",
        "name": "Alerta de Incidente Crítico (Suporte)",
        "is_active": False,
        "flow_data": _flow_critical_incident(),
    },
    {
        "system_key": "restock_request",
        "name": "Solicitação de Reposição",
        "is_active": False,
        "flow_data": _flow_restock_request(),
    },
]


def seed_system_workflows(tenant_id: int, *, force: bool = False) -> int:
    """
    Cria fluxos padrão faltantes para o tenant.
    Retorna a quantidade de registros criados. Idempotente por system_key.
    """
    created_count = 0
    for template in SYSTEM_WORKFLOW_TEMPLATES:
        system_key = template["system_key"]
        exists = ChatbotWorkflow.all_objects.filter(
            tenant_id=tenant_id,
            system_key=system_key,
        ).exists()
        if exists and not force:
            continue

        flow_data = validate_flow_data(template["flow_data"])
        if exists and force:
            ChatbotWorkflow.all_objects.filter(
                tenant_id=tenant_id,
                system_key=system_key,
            ).update(
                name=template["name"],
                flow_data=flow_data,
                is_system=True,
            )
            continue

        ChatbotWorkflow.all_objects.create(
            tenant_id=tenant_id,
            name=template["name"],
            system_key=system_key,
            is_system=True,
            is_active=template["is_active"],
            flow_data=flow_data,
        )
        created_count += 1

    return created_count

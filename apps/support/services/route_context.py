from __future__ import annotations

from urllib.parse import parse_qs, urlparse

SUPPORT_BASE_SYSTEM = """Você é o Suporte Copilot do Marketchat, plataforma de mercados autônomos com atendimento e vendas via WhatsApp.

Regras:
- Responda sempre em português do Brasil, de forma direta e objetiva (suporte técnico).
- Use apenas funcionalidades reais do painel admin; não invente telas, APIs ou status que não existam.
- Cite nomes de menu da sidebar quando orientar navegação: Dashboard, Histórico de Chamados, Painel de Vendas, Moradores, Produtos, Configurações (Mercados, Integrações, Minha Conta, Plano e pagamento, Histórico de Faturas).
- Se não souber algo específico da conta do usuário, diga o que ele pode verificar na tela ou nas Configurações.
"""

_ROUTE_CONTEXTS: list[tuple[bool, str]] = [
    (
        lambda r, p, q: "/admin/products" in p,
        (
            "O usuário está na tela de Produtos e importação de catálogo. "
            "Oriente a baixar sempre a planilha modelo padrão antes do upload para evitar erros de formatação. "
            "Explique o fluxo: download do modelo → preenchimento → upload → preview → confirmação da importação. "
            "Mencione busca, edição de produto e status ativo/inativo quando relevante."
        ),
    ),
    (
        lambda r, p, q: "section=integrations" in r and "tab=pix" in r,
        (
            "O usuário está em Configurações → Integrações → Recebimentos (Pix/subconta Asaas). "
            "Explique cadastro de chave Pix, tipos de chave (CPF, CNPJ, e-mail, telefone, aleatória), "
            "necessidade de pelo menos um mercado com endereço completo para criar a subconta, "
            "e status da conta (PENDING, APPROVED, REJECTED). "
            "Valores de vendas no WhatsApp caem na conta do operador após aprovação."
        ),
    ),
    (
        lambda r, p, q: "section=integrations" in r or "whatsapp" in r,
        (
            "O usuário está configurando a conexão do Robô do WhatsApp (Integrações). "
            "Explique que o QR Code gerado na tela precisa ser escaneado em "
            '"Aparelhos conectados" no WhatsApp do celular (não no app Marketchat). '
            "O processo leva alguns segundos para inicializar após escanear. "
            "Se aparecer erro ao reiniciar ou 502, pode ser corrida: QR ainda não disponível — tentar Conectar de novo. "
            "Recomende número dedicado ao negócio quando perguntarem sobre número pessoal."
        ),
    ),
    (
        lambda r, p, q: "/admin/chat-logs" in p,
        (
            "O usuário está no Histórico de Chamados (conversas WhatsApp). "
            "Ajude a filtrar por mercado e data, abrir o drawer da conversa completa, "
            "e interpretar mensagens inbound (morador) vs outbound (bot/sistema). "
            "Não mencione Kanban nem status PENDING/ANALYZING — essa tela é histórico, não quadro de tickets."
        ),
    ),
    (
        lambda r, p, q: "/admin/sales" in p,
        (
            "O usuário está no Painel de Vendas. "
            "Ajude com KPIs (faturamento, pedidos, ticket médio), lista de pedidos, "
            "fotos de segurança enviadas antes do pagamento e filtros por período/mercado."
        ),
    ),
    (
        lambda r, p, q: "/admin/residents" in p,
        (
            "O usuário está na tela de Moradores cadastrados via WhatsApp. "
            "Explique cadastro pelo fluxo do bot, vínculo ao condomínio/mercado e busca na lista."
        ),
    ),
    (
        lambda r, p, q: "/admin/chatbot-flows" in p,
        (
            "O usuário está no editor visual de Fluxos do chatbot (React Flow). "
            "Tipos de nó: trigger (início), ai_filter (roteamento por intenção), response (resposta), "
            "owner_alert (alerta à gerência). Vários fluxos podem estar ativos; fluxos do sistema não podem ser renomeados."
        ),
    ),
    (
        lambda r, p, q: "section=markets" in r,
        (
            "O usuário está em Configurações → Mercados (condomínios). "
            "Oriente cadastro de nome, endereço completo (CEP, rua, número, bairro, cidade, UF) "
            "e status ativo/inativo — endereço é necessário para Pix e contexto do bot."
        ),
    ),
    (
        lambda r, p, q: "tab=plan" in r or "tab=history" in r,
        (
            "O usuário está em Plano e pagamento ou Histórico de Faturas. "
            "Ajude com trial, assinatura, cartão de crédito, reativação, faturas pagas/pendentes/atrasadas "
            "e acesso durante período de carência."
        ),
    ),
    (
        lambda r, p, q: p.rstrip("/") == "/admin",
        (
            "O usuário está no Dashboard (BI operacional do chatbot). "
            "Ajude a interpretar: interações no mês, incidentes críticos (geladeira, maquininha, produto estragado), "
            "sessões automatizadas resolvidas pela IA, alertas à gerência (support tickets), sessões canceladas/abandonadas, "
            "gráficos de estabilidade por mercado e filtro por condomínio. "
            "Onboarding pode estar visível até concluir missões iniciais."
        ),
    ),
]

_FALLBACK_CONTEXT = (
    "O usuário está em outra área do painel Marketchat ou rota genérica. "
    "Atue como assistente geral: mercados autônomos, robô WhatsApp, catálogo, vendas Pix, "
    "dashboard e configurações. Sugira o menu correto da sidebar para a dúvida dele."
)


def _parse_route(current_route: str) -> tuple[str, str, dict[str, list[str]]]:
    raw = (current_route or "").strip()
    if not raw:
        return "", "", {}
    if "://" in raw:
        parsed = urlparse(raw)
        path = parsed.path or ""
        query = parse_qs(parsed.query)
    elif "?" in raw:
        path, qs = raw.split("?", 1)
        query = parse_qs(qs)
    else:
        path = raw
        query = {}
    route_lower = raw.lower()
    path_lower = path.lower()
    return route_lower, path_lower, query


def resolve_route_context(current_route: str) -> str:
    """Retorna bloco de contexto dinâmico para anexar ao system prompt."""
    route_lower, path_lower, _query = _parse_route(current_route)
    for matcher, context in _ROUTE_CONTEXTS:
        if matcher(route_lower, path_lower, _query):
            return context
    return _FALLBACK_CONTEXT


def build_support_system_prompt(current_route: str) -> str:
    dynamic = resolve_route_context(current_route).strip()
    return f"{SUPPORT_BASE_SYSTEM.strip()}\n\nContexto da tela atual:\n{dynamic}"

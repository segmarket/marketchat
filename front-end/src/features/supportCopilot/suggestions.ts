function routeKey(pathname: string, search: string): string {
  const route = `${pathname}${search}`.toLowerCase();
  if (route.includes("/admin/products")) return "products";
  if (route.includes("section=integrations") && route.includes("tab=pix")) return "pix";
  if (route.includes("section=integrations")) return "whatsapp";
  if (route.includes("/admin/chat-logs")) return "chat-logs";
  if (route.includes("/admin/sales")) return "sales";
  if (route.includes("/admin/residents")) return "residents";
  if (route.includes("/admin/chatbot-flows")) return "chatbot-flows";
  if (route.includes("section=markets")) return "markets";
  if (route.includes("tab=plan") || route.includes("tab=history")) return "billing";
  if (pathname === "/admin" || pathname === "/admin/") return "dashboard";
  return "fallback";
}

const SUGGESTIONS: Record<string, string[]> = {
  whatsapp: [
    "E se o QR Code expirar?",
    "Posso usar meu número pessoal?",
    "O robô não conecta após escanear",
  ],
  pix: [
    "Por que preciso cadastrar um mercado?",
    "O que significa status PENDING?",
    "Quais tipos de chave Pix posso usar?",
  ],
  products: [
    "Como baixar a planilha modelo?",
    "Erros comuns na importação",
    "Posso editar produto depois de importar?",
  ],
  dashboard: [
    "O que é incidente crítico?",
    "Como filtrar por condomínio?",
    "O que são sessões automatizadas?",
  ],
  "chat-logs": [
    "Como abrir a conversa completa?",
    "Diferença entre inbound e outbound",
    "Como filtrar por data?",
  ],
  sales: [
    "O que é ticket médio?",
    "Para que serve a foto de segurança?",
    "Como ver detalhes do pedido?",
  ],
  residents: [
    "Como o morador se cadastra?",
    "Posso mudar o mercado do morador?",
    "O morador não aparece na lista",
  ],
  "chatbot-flows": [
    "Quais tipos de nó existem?",
    "Posso ter vários fluxos ativos?",
    "O que faz o nó owner_alert?",
  ],
  markets: [
    "Por que o endereço é obrigatório?",
    "Posso desativar um mercado?",
    "Quantos mercados posso cadastrar?",
  ],
  billing: [
    "Como atualizar o cartão?",
    "O que acontece se a fatura atrasar?",
    "Como funciona o período de trial?",
  ],
  fallback: [
    "Por onde começo no Marketchat?",
    "Como conectar o WhatsApp?",
    "Como importar produtos?",
  ],
};

export function getQuickSuggestions(pathname: string, search: string): string[] {
  const key = routeKey(pathname, search);
  return SUGGESTIONS[key] ?? SUGGESTIONS.fallback;
}

export function buildCurrentRoute(pathname: string, search: string): string {
  return `${pathname}${search}`;
}

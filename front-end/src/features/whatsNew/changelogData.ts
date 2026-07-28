export const CURRENT_VERSION = "v1.3.0";

export const LAST_SEEN_VERSION_KEY = "marketChat_lastSeenVersion";

export type ChangelogIconName =
  | "Clock"
  | "Power"
  | "MessagesSquare"
  | "Receipt"
  | "ListChecks";

export type ChangelogItem = {
  id: string;
  title: string;
  description: string;
  icon: ChangelogIconName;
};

export const CHANGELOG_ITEMS: ChangelogItem[] = [
  {
    id: "bot-schedule",
    title: "Horário de Atendimento Automático",
    description:
      "Defina o seu horário comercial! Agora o bot pausa sozinho enquanto sua equipe trabalha e assume os atendimentos automaticamente nas madrugadas, folgas e finais de semana.",
    icon: "Clock",
  },
  {
    id: "bot-master-switch",
    title: "Chave Geral do Robô",
    description:
      "Assuma o controle total. Precisa usar o WhatsApp livremente num feriado? Use a nova Chave Geral para pausar o robô com um único clique, sem perder suas configurações.",
    icon: "Power",
  },
  {
    id: "whatsapp-web-chat",
    title: "Novo Chat estilo WhatsApp Web",
    description:
      "Atenda seus clientes em uma interface moderna, em tempo real e com alertas sonoros.",
    icon: "MessagesSquare",
  },
  {
    id: "express-charge",
    title: "Cobrança Expressa no Chat",
    description:
      "Gere cobranças e PIX Copia e Cola sem sair da tela de atendimento.",
    icon: "Receipt",
  },
  {
    id: "interactive-menu",
    title: "Menu Interativo",
    description:
      "Seus clientes agora escolhem o motivo do contato através de uma lista clicável no próprio WhatsApp.",
    icon: "ListChecks",
  },
];

export const CURRENT_VERSION = "v1.2.0";

export const LAST_SEEN_VERSION_KEY = "marketChat_lastSeenVersion";

export type ChangelogIconName = "MessagesSquare" | "Receipt" | "ListChecks";

export type ChangelogItem = {
  id: string;
  title: string;
  description: string;
  icon: ChangelogIconName;
};

export const CHANGELOG_ITEMS: ChangelogItem[] = [
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

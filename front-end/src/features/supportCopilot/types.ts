export type SupportChatRole = "user" | "assistant";

export type SupportChatMessage = {
  role: SupportChatRole;
  content: string;
};

export type SupportChatRequest = {
  message: string;
  current_route: string;
  chat_history?: SupportChatMessage[];
};

export type SupportChatResponse = {
  reply: string;
};

export type SupportTicketRequest = {
  subject: string;
  description: string;
  category_route: string;
};

export type SupportTicketResponse = {
  id: number;
  subject: string;
  status: string;
  priority: string;
  created_at: string;
};

export type CopilotPanelMode = "chat" | "ticket" | "ticket_sent";

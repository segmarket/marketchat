import type { SupportChatMessage } from "./types";

const TRANSCRIPT_MAX_MESSAGES = 10;

export function formatChatTranscript(messages: SupportChatMessage[]): string {
  if (messages.length === 0) {
    return "";
  }
  const slice = messages.slice(-TRANSCRIPT_MAX_MESSAGES);
  const lines = slice.map((msg) => {
    const label = msg.role === "user" ? "Usuário" : "Copilot";
    return `${label}: ${msg.content}`;
  });
  return `Histórico do Suporte Copilot:\n${lines.join("\n")}\n\nRelato adicional:\n`;
}

export function suggestTicketSubject(messages: SupportChatMessage[]): string {
  const lastUser = [...messages].reverse().find((m) => m.role === "user");
  if (!lastUser?.content.trim()) {
    return "";
  }
  const text = lastUser.content.trim().replace(/\s+/g, " ");
  return text.length > 80 ? `${text.slice(0, 77)}...` : text;
}

export function buildTicketDescriptionPrefill(messages: SupportChatMessage[]): string {
  const transcript = formatChatTranscript(messages);
  return transcript || "Relato adicional:\n";
}

import { api } from "../../services/api";
import type {
  AgentMessageResponse,
  ChatBotStatusResponse,
  ChatConversationResponse,
  ChatLogsListResponse,
  InboxSessionsListResponse,
} from "./types";

export async function fetchChatLogs(
  params: Record<string, string | number>,
): Promise<ChatLogsListResponse> {
  const { data } = await api.get<ChatLogsListResponse>("/api/chatbot/logs/", { params });
  return data;
}

export type FetchInboxSessionsParams = {
  botActive?: boolean | null;
  page?: number;
  q?: string;
};

export async function fetchInboxSessions(
  params: FetchInboxSessionsParams = {},
): Promise<InboxSessionsListResponse> {
  const query: Record<string, string | number> = {};
  if (params.page != null) query.page = params.page;
  if (params.q) query.q = params.q;
  if (params.botActive === true) query.bot_active = "true";
  if (params.botActive === false) query.bot_active = "false";

  const { data } = await api.get<InboxSessionsListResponse>("/api/chatbot/sessions/", {
    params: query,
  });
  return data;
}

export type FetchConversationOptions = {
  date?: string;
  afterId?: number;
};

export async function fetchConversation(
  sessionId: number,
  options: FetchConversationOptions | string = {},
): Promise<ChatConversationResponse> {
  const opts: FetchConversationOptions =
    typeof options === "string" ? { date: options } : options;

  const params: Record<string, string | number> = {
    session_id: sessionId,
  };
  if (opts.date) params.date = opts.date;
  if (opts.afterId != null && opts.afterId > 0) params.after_id = opts.afterId;

  const { data } = await api.get<ChatConversationResponse>(
    "/api/chatbot/logs/conversation/",
    { params },
  );
  return data;
}

export async function fetchChatMessageAttachment(messageId: number): Promise<Blob> {
  const { data } = await api.get<Blob>(`/api/chatbot/messages/${messageId}/attachment/`, {
    responseType: "blob",
  });
  return data;
}

export async function toggleSessionBot(
  sessionId: number,
  isBotActive: boolean,
): Promise<ChatBotStatusResponse> {
  const { data } = await api.patch<ChatBotStatusResponse>(
    `/api/chatbot/sessions/${sessionId}/toggle-bot/`,
    { is_bot_active: isBotActive },
  );
  return data;
}

export async function sendAgentMessage(
  sessionId: number,
  text: string,
): Promise<AgentMessageResponse> {
  const { data } = await api.post<AgentMessageResponse>(
    `/api/chatbot/sessions/${sessionId}/messages/`,
    { text },
  );
  return data;
}

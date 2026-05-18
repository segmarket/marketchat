import { api } from "../../services/api";
import type { ChatConversationResponse, ChatLogsListResponse } from "./types";

export async function fetchChatLogs(
  params: Record<string, string | number>,
): Promise<ChatLogsListResponse> {
  const { data } = await api.get<ChatLogsListResponse>("/api/chatbot/logs/", { params });
  return data;
}

export async function fetchConversation(
  sessionId: number,
  attendanceDate: string,
): Promise<ChatConversationResponse> {
  const { data } = await api.get<ChatConversationResponse>(
    "/api/chatbot/logs/conversation/",
    {
      params: {
        session_id: sessionId,
        date: attendanceDate,
      },
    },
  );
  return data;
}

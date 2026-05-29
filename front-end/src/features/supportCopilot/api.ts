import { api } from "../../services/api";
import type {
  SupportChatRequest,
  SupportChatResponse,
  SupportTicketRequest,
  SupportTicketResponse,
} from "./types";

export async function postSupportChat(
  payload: SupportChatRequest,
): Promise<SupportChatResponse> {
  const { data } = await api.post<SupportChatResponse>("/api/support/chat/", payload);
  return data;
}

export async function postSupportTicket(
  payload: SupportTicketRequest,
): Promise<SupportTicketResponse> {
  const { data } = await api.post<SupportTicketResponse>("/api/support/tickets/", payload);
  return data;
}

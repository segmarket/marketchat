import { api } from "../../services/api";
import type {
  SupportTicketDetail,
  SupportTicketReplyResponse,
  SupportTicketSummary,
} from "./types";

export async function fetchSupportTickets(): Promise<SupportTicketSummary[]> {
  const { data } = await api.get<SupportTicketSummary[]>("/api/support/tickets/");
  return data;
}

export async function fetchSupportTicket(id: number): Promise<SupportTicketDetail> {
  const { data } = await api.get<SupportTicketDetail>(`/api/support/tickets/${id}/`);
  return data;
}

export async function postSupportTicketReply(
  id: number,
  message: string,
): Promise<SupportTicketReplyResponse> {
  const { data } = await api.post<SupportTicketReplyResponse>(
    `/api/support/tickets/${id}/reply/`,
    { message },
  );
  return data;
}

export async function patchSupportTicket(
  id: number,
  payload: { status: "RESOLVED" | "CLOSED" },
): Promise<SupportTicketDetail> {
  const { data } = await api.patch<SupportTicketDetail>(`/api/support/tickets/${id}/`, payload);
  return data;
}

import { api } from "../../services/api";
import type { ChatbotWorkflow, ChatbotWorkflowSummary, SaveWorkflowPayload } from "./types";

export async function fetchChatbotWorkflows(): Promise<ChatbotWorkflowSummary[]> {
  const { data } = await api.get<ChatbotWorkflowSummary[]>("/api/chatbot/workflows/");
  return data;
}

export async function fetchActiveChatbotWorkflow(): Promise<ChatbotWorkflow | null> {
  try {
    const { data } = await api.get<ChatbotWorkflow>("/api/chatbot/workflows/active/");
    return data;
  } catch (err: unknown) {
    const status = (err as { response?: { status?: number } })?.response?.status;
    if (status === 404) return null;
    throw err;
  }
}

export async function fetchChatbotWorkflow(id: number): Promise<ChatbotWorkflow> {
  const { data } = await api.get<ChatbotWorkflow>(`/api/chatbot/workflows/${id}/`);
  return data;
}

export async function patchChatbotWorkflow(
  id: number,
  payload: { name?: string; is_active?: boolean },
): Promise<ChatbotWorkflow> {
  const { data } = await api.patch<ChatbotWorkflow>(`/api/chatbot/workflows/${id}/`, payload);
  return data;
}

export async function deleteChatbotWorkflow(id: number): Promise<void> {
  await api.delete(`/api/chatbot/workflows/${id}/`);
}

export async function duplicateChatbotWorkflow(id: number): Promise<ChatbotWorkflow> {
  const { data } = await api.post<ChatbotWorkflow>(`/api/chatbot/workflows/${id}/duplicate/`);
  return data;
}

export async function saveChatbotWorkflow(payload: SaveWorkflowPayload): Promise<ChatbotWorkflow> {
  const { data } = await api.post<ChatbotWorkflow>("/api/chatbot/workflows/save/", payload);
  return data;
}

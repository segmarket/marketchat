import { api } from "../../services/api";
import type { ChatbotAnalyticsResponse } from "./types";

export async function fetchChatbotAnalytics(
  marketId?: number | null,
): Promise<ChatbotAnalyticsResponse> {
  const params: Record<string, number> = {};
  if (marketId != null && marketId > 0) {
    params.market_id = marketId;
  }
  const { data } = await api.get<ChatbotAnalyticsResponse>("/api/chatbot/analytics/", {
    params,
  });
  return data;
}

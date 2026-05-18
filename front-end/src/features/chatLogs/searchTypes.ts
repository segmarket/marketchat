import { digitsOnly } from "../residents/format";
import type { IntentType } from "./types";

export type ChatLogsSearchFilters = {
  residentName: string;
  phone: string;
  marketId: string;
  intentType: IntentType | "";
  date: string;
};

export function emptyChatLogsSearchFilters(): ChatLogsSearchFilters {
  return {
    residentName: "",
    phone: "",
    marketId: "",
    intentType: "",
    date: "",
  };
}

export function hasActiveChatLogsFilters(filters: ChatLogsSearchFilters): boolean {
  return Boolean(
    filters.residentName.trim()
      || digitsOnly(filters.phone)
      || filters.marketId
      || filters.intentType
      || filters.date,
  );
}

export function buildChatLogsQueryParams(
  filters: ChatLogsSearchFilters,
  page: number,
): Record<string, string | number> {
  const params: Record<string, string | number> = { page };
  const name = filters.residentName.trim();
  const phone = digitsOnly(filters.phone);
  if (name) params.resident_name = name;
  if (phone) params.phone = phone;
  if (filters.marketId) params.market_id = filters.marketId;
  if (filters.intentType) params.intent_type = filters.intentType;
  if (filters.date) params.date = filters.date;
  return params;
}

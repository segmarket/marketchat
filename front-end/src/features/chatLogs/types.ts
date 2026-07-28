export type IntentType =
  | "PURCHASE"
  | "MAINTENANCE_ISSUE"
  | "COMPLAINT"
  | "PAYMENT_ERROR"
  | "STOCK_ISSUE"
  | "GENERAL"
  | "";

export type ChatAttendanceRow = {
  session_id: number;
  attendance_date: string;
  resident_name: string;
  resident_phone: string;
  market_name: string;
  intent_type: IntentType;
  last_at: string;
  message_count: number;
  preview: string;
};

export type InboxSessionRow = {
  session_id: number;
  resident_name: string;
  resident_phone: string;
  market_name: string;
  is_bot_active: boolean;
  last_at: string;
  preview: string;
  last_direction: "INBOUND" | "OUTBOUND" | "AGENT" | "";
  last_inbound_id: number | null;
};

export type InboxSessionsListResponse = {
  count: number;
  next: number | null;
  previous: number | null;
  results: InboxSessionRow[];
};

export type ChatLogsListResponse = {
  count: number;
  next: number | null;
  previous: number | null;
  results: ChatAttendanceRow[];
};

export type ChatLogMessage = {
  id: number;
  direction: "INBOUND" | "OUTBOUND" | "AGENT";
  message_text: string;
  intent_type: string;
  message_kind: string;
  created_at: string;
  attachment_url: string;
};

export type ChatConversationResponse = {
  session_id: number;
  resident_name: string;
  resident_phone: string;
  market_name: string;
  attendance_date: string;
  is_bot_active: boolean;
  resident_billing_identified: boolean;
  last_human_interaction_at: string | null;
  client_is_typing?: boolean;
  messages: ChatLogMessage[];
};

export type ChatBotStatusResponse = {
  is_bot_active: boolean;
  last_human_interaction_at: string | null;
};

export type AgentMessageResponse = ChatBotStatusResponse & {
  message: ChatLogMessage | null;
};

export type ChatLogsMarketOption = {
  id: number;
  name: string;
};

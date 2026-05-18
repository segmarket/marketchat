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

export type ChatLogsListResponse = {
  count: number;
  next: number | null;
  previous: number | null;
  results: ChatAttendanceRow[];
};

export type ChatLogMessage = {
  id: number;
  direction: "INBOUND" | "OUTBOUND";
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
  messages: ChatLogMessage[];
};

export type ChatLogsMarketOption = {
  id: number;
  name: string;
};

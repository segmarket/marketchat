export type NotificationSeverity = "CRITICAL" | "WARNING" | "INFO";

export type NotificationItem = {
  id: number;
  title: string;
  message: string;
  severity: NotificationSeverity;
  is_read: boolean;
  created_at: string;
  market_id: number | null;
  market_name: string | null;
  intent_type: string;
};

export type NotificationsLatestResponse = {
  unread_count: number;
  results: NotificationItem[];
};

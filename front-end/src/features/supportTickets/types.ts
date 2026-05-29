export type SupportTicketStatus = "NEW" | "IN_PROGRESS" | "RESOLVED" | "CLOSED";

export type SupportTicketMessage = {
  id: number;
  sender_email: string;
  sender_name: string;
  is_from_admin: boolean;
  message: string;
  created_at: string;
};

export type SupportTicketSummary = {
  id: number;
  subject: string;
  status: SupportTicketStatus;
  priority: string;
  category_route: string;
  created_at: string;
  updated_at: string;
  user_email: string;
  message_count: number;
};

export type SupportTicketDetail = SupportTicketSummary & {
  description: string;
  messages: SupportTicketMessage[];
};

export type SupportTicketReplyResponse = {
  ticket_id: number;
  status: SupportTicketStatus;
  message: SupportTicketMessage;
};

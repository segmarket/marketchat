import { api } from "../../services/api";

export type ChatPixItemInput = {
  name: string;
  quantity: number;
  unit_price: string;
};

export type ChatPixItemSummary = {
  name: string;
  quantity: number;
  unit_price: string;
  subtotal: string;
};

export type GenerateChatPixPayload = {
  sessionId: number;
  items?: ChatPixItemInput[];
  amount?: string;
  description?: string;
  deliverWhatsapp?: boolean;
};

export type GenerateChatPixResponse = {
  pix_copia_e_cola: string;
  invoice_url: string;
  amount: string;
  cart_id: number;
  description: string;
  items_summary: ChatPixItemSummary[];
  billing_mode?: "resident" | "walk_in";
  message_summary: string;
  message_pix: string;
  delivered_whatsapp?: boolean;
};

export async function generateChatPix(
  payload: GenerateChatPixPayload,
): Promise<GenerateChatPixResponse> {
  const body: Record<string, unknown> = {
    session_id: payload.sessionId,
    deliver_whatsapp: payload.deliverWhatsapp ?? false,
  };
  if (payload.amount) {
    body.amount = payload.amount;
  } else if (payload.items?.length) {
    body.items = payload.items;
  }
  if (payload.description) {
    body.description = payload.description;
  }

  const { data } = await api.post<GenerateChatPixResponse>(
    "/api/payments/generate-pix-chat/",
    body,
  );
  return data;
}

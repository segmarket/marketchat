import { api } from "../../services/api";
import { formatBRL } from "../financial/format";

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
};

export type GenerateChatPixResponse = {
  pix_copia_e_cola: string;
  invoice_url: string;
  amount: string;
  cart_id: number;
  description: string;
  items_summary: ChatPixItemSummary[];
};

export async function generateChatPix(
  payload: GenerateChatPixPayload,
): Promise<GenerateChatPixResponse> {
  const body: Record<string, unknown> = {
    session_id: payload.sessionId,
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

/** Monta o texto a injetar no composer do atendente. */
export function formatChatPixMessage(data: GenerateChatPixResponse): string {
  const itemsLabel = data.items_summary
    .map((item) => {
      if (item.name === "Cobrança avulsa" && item.quantity === 1) {
        return "cobrança avulsa";
      }
      return `${item.name} (${item.quantity}x)`;
    })
    .join(", ");

  const total = formatBRL(data.amount);
  const lines = [
    `Aqui está o resumo do seu pedido: ${itemsLabel}.`,
    `Total: ${total}.`,
    "",
    "Para pagar via PIX Copia e Cola, use o código abaixo:",
    data.pix_copia_e_cola,
  ];

  if (data.invoice_url) {
    lines.push("", `Ou acesse o link de pagamento: ${data.invoice_url}`);
  }

  return lines.join("\n");
}

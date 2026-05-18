const BILLING_TYPE_LABELS: Record<string, string> = {
  CREDIT_CARD: "Cartão",
  BOLETO: "Boleto",
  PIX: "Pix",
  DEBIT_CARD: "Débito",
  UNDEFINED: "—",
};

export function billingTypeLabel(type: string): string {
  return BILLING_TYPE_LABELS[type] ?? type;
}

export function formatCurrencyBRL(value: number): string {
  return new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" }).format(value);
}

export function formatDateBR(isoDate: string): string {
  if (!isoDate) return "—";
  const [y, m, d] = isoDate.split("-");
  if (!y || !m || !d) return isoDate;
  return `${d}/${m}/${y}`;
}

export function billingErrorMessage(err: unknown): string {
  if (
    typeof err === "object" &&
    err !== null &&
    "response" in err &&
    (err as { response?: { status?: number } }).response?.status === 502
  ) {
    return "Serviço de pagamentos temporariamente indisponível. Tente novamente em instantes.";
  }
  return "";
}

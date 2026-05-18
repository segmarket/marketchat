import type { CartStatus } from "./types";

export const STATUS_OPTIONS: { value: CartStatus; label: string }[] = [
  { value: "", label: "Todos os status" },
  { value: "COMPLETED", label: "Concluído" },
  { value: "AWAITING_PAYMENT", label: "Aguardando pagamento" },
  { value: "AWAITING_PHOTO", label: "Aguardando foto" },
  { value: "OPEN", label: "Aberto" },
  { value: "CANCELLED", label: "Cancelado" },
  { value: "EXPIRED", label: "Pix expirado" },
];

export function cartStatusLabel(status: string): string {
  const found = STATUS_OPTIONS.find((o) => o.value === status);
  return found?.label ?? (status || "—");
}

export function cartStatusBadgeClass(status: string): string {
  switch (status) {
    case "COMPLETED":
      return "bg-emerald-50 text-emerald-700 ring-emerald-600/20";
    case "AWAITING_PAYMENT":
      return "bg-blue-50 text-blue-700 ring-blue-600/20";
    case "AWAITING_PHOTO":
      return "bg-violet-50 text-violet-700 ring-violet-600/20";
    case "OPEN":
      return "bg-gray-100 text-gray-700 ring-gray-500/20";
    case "CANCELLED":
    case "EXPIRED":
      return "bg-red-50 text-red-700 ring-red-600/20";
    default:
      return "bg-gray-100 text-gray-700 ring-gray-500/20";
  }
}

export function formatBRL(value: string | number): string {
  const num = typeof value === "string" ? Number.parseFloat(value) : value;
  if (!Number.isFinite(num)) return "R$ 0,00";
  return new Intl.NumberFormat("pt-BR", {
    style: "currency",
    currency: "BRL",
  }).format(num);
}

export function formatPercent(rate: number): string {
  if (!Number.isFinite(rate)) return "0%";
  return new Intl.NumberFormat("pt-BR", {
    style: "percent",
    maximumFractionDigits: 1,
  }).format(rate);
}

export function formatOrderDateTime(iso: string): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso;
  return new Intl.DateTimeFormat("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
}

export function formatConversionTooltip(rate: number): string {
  return `Taxa de conversão: ${formatPercent(rate)} dos carrinhos do período viraram venda concluída.`;
}

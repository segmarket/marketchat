import type { IntentType } from "./types";

export const INTENT_OPTIONS: { value: IntentType | ""; label: string }[] = [
  { value: "", label: "Todos os tipos" },
  { value: "PURCHASE", label: "Compra" },
  { value: "MAINTENANCE_ISSUE", label: "Manutenção" },
  { value: "COMPLAINT", label: "Reclamação" },
  { value: "PAYMENT_ERROR", label: "Erro de pagamento" },
  { value: "STOCK_ISSUE", label: "Falta de estoque" },
  { value: "GENERAL", label: "Geral" },
];

export function intentTypeLabel(intent: string): string {
  const found = INTENT_OPTIONS.find((o) => o.value === intent);
  return found?.label ?? (intent || "—");
}

export function intentBadgeClass(intent: string): string {
  switch (intent) {
    case "PURCHASE":
      return "bg-emerald-50 text-emerald-700 ring-emerald-600/20";
    case "MAINTENANCE_ISSUE":
      return "bg-amber-50 text-amber-800 ring-amber-600/20";
    case "COMPLAINT":
      return "bg-orange-50 text-orange-800 ring-orange-600/20";
    case "PAYMENT_ERROR":
      return "bg-red-50 text-red-700 ring-red-600/20";
    case "STOCK_ISSUE":
      return "bg-yellow-50 text-yellow-800 ring-yellow-600/20";
    case "GENERAL":
    default:
      return "bg-gray-100 text-gray-700 ring-gray-500/20";
  }
}

export function formatAttendanceDateTime(iso: string): string {
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

export function formatAttendanceDateOnly(iso: string): string {
  if (!iso) return "";
  const [y, m, d] = iso.split("-");
  if (y && m && d) return `${d}/${m}/${y}`;
  return iso;
}

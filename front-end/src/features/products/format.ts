import type { ProductStatus } from "./types";

export function formatCurrencyBRL(value: string | number): string {
  const num = typeof value === "string" ? Number.parseFloat(value) : value;
  if (Number.isNaN(num)) return String(value);
  return new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" }).format(num);
}

export function statusLabel(status: ProductStatus): string {
  return status === "active" ? "Ativo" : "Inativo";
}

export function statusBadgeColor(status: ProductStatus): "success" | "error" {
  return status === "active" ? "success" : "error";
}

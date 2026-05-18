import type { MarketStatus } from "./types";

export function statusLabel(status: MarketStatus): string {
  return status === "active" ? "Ativo" : "Inativo";
}

export function statusBadgeColor(status: MarketStatus): "success" | "error" {
  return status === "active" ? "success" : "error";
}

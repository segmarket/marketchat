import type { PixKeyType } from "./types";

const LABELS: Record<PixKeyType, string> = {
  CPF: "CPF",
  CNPJ: "CNPJ",
  EMAIL: "E-mail",
  PHONE: "Celular",
  RANDOM: "Chave aleatória",
};

export function pixKeyTypeLabel(type: PixKeyType | ""): string {
  if (!type) return "";
  return LABELS[type] ?? type;
}

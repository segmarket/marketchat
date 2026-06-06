import type { PixKeyType } from "./types";

export const MASK_INPUT_CLASS =
  "h-11 w-full rounded-lg border border-gray-300 bg-transparent px-4 py-2.5 text-sm shadow-theme-xs placeholder:text-gray-400 focus:border-brand-300 focus:outline-none focus:ring-2 focus:ring-brand-500/20 dark:border-gray-700 dark:text-white/90";

export function pixKeyMaskForType(type: PixKeyType): { mask?: string } {
  switch (type) {
    case "CPF":
      return { mask: "000.000.000-00" };
    case "CNPJ":
      return { mask: "00.000.000/0000-00" };
    case "PHONE":
      return { mask: "(00) 00000-0000" };
    case "EMAIL":
    case "RANDOM":
    default:
      return {};
  }
}

export function pixKeyPlaceholder(type: PixKeyType): string {
  switch (type) {
    case "CPF":
      return "000.000.000-00";
    case "CNPJ":
      return "00.000.000/0000-00";
    case "PHONE":
      return "(11) 99999-9999";
    case "EMAIL":
      return "seu@email.com";
    case "RANDOM":
      return "Chave aleatória (EVP)";
    default:
      return "";
  }
}

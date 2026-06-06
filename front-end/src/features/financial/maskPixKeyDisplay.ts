import { digitsOnly } from "../../utils/cpfCnpj";
import type { PixKeyType } from "./types";

export function maskPixKeyDisplay(type: PixKeyType | "", key: string): string {
  if (!key || !type) return "";

  if (type === "EMAIL") {
    const [local, domain] = key.split("@");
    if (!domain) return "***";
    const visible = local.length > 2 ? local.slice(0, 2) : local.slice(0, 1) || "*";
    return `${visible}***@${domain}`;
  }

  if (type === "RANDOM") {
    if (key.length <= 4) return "****";
    return `****…${key.slice(-4)}`;
  }

  const digits = digitsOnly(key);
  if (digits.length <= 4) return "****";

  const last4 = digits.slice(-4);

  if (type === "CPF") {
    return `***.***.${last4.slice(0, 3)}-${last4.slice(3)}`;
  }

  if (type === "CNPJ") {
    return `**.***.***/${last4.slice(0, 2)}${last4.slice(2)}-**`;
  }

  if (type === "PHONE") {
    if (digits.length === 11) {
      return `(**) *****-${last4}`;
    }
    return `(**) ****-${last4}`;
  }

  return `${"*".repeat(Math.max(0, digits.length - 4))}${last4}`;
}

/** Dados corporativos e textos legais (privacidade, termos). */

export const COMPANY_LEGAL_NAME = "Viva Software";
export const COMPANY_CNPJ = "35.960.300/0001-05";
export const DPO_EMAIL = "contato@marketchat.com.br";
export const LEGAL_CONTACT_EMAIL = "contato@marketchat.com.br";
export const LEGAL_LAST_UPDATED = "25 de maio de 2026";

export function platformFeePercentLabel(): string {
  const raw = import.meta.env.VITE_PLATFORM_FEE_PERCENT?.trim();
  if (raw) return raw.replace(".", ",");
  return "2";
}

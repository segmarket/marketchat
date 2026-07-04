/** Dados corporativos e textos legais (privacidade, termos). */

export const COMPANY_LEGAL_NAME = "SMS SISTEMAS";
export const COMPANY_TRADE_NAME = "MarketChat";
export const PRODUCT_NAME = "MarketChat";
export const COMPANY_CNPJ = "67.682.023/0001-02";
export const COMPANY_CNPJ_DIGITS = "67682023000102";
export const COMPANY_ADDRESS_LINES = [
  "Av. Guilherme de Paula Xavier, 2956",
  "Jardim São Sebastião, Campo Mourão - PR",
  "CEP 87303-309",
] as const;
export const COMPANY_LEGAL_INTRO =
  "A MarketChat, operada por SMS SISTEMAS INOVA SIMPLES (I.S.), CNPJ 67.682.023/0001-02, localizada na Av. Guilherme de Paula Xavier, 2956, Jardim São Sebastião, Campo Mourão/PR, CEP 87303-309";
export const DPO_EMAIL = "contato@marketchat.com.br";
export const LEGAL_CONTACT_EMAIL = "contato@marketchat.com.br";
export const LEGAL_LAST_UPDATED = "25 de maio de 2026";

export function platformFeePercentLabel(): string {
  const raw = import.meta.env.VITE_PLATFORM_FEE_PERCENT?.trim();
  if (raw) return raw.replace(".", ",");
  return "2";
}

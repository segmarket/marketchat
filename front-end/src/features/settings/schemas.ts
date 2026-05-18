import { z } from "zod";
import { isValidUFSigla } from "../../constants/brazilUF";
import { digitsOnly, isValidCpfOrCnpj } from "../../utils/cpfCnpj";
import { step3Schema } from "../signup/schema";

export const accountSettingsSchema = z.object({
  first_name: z.string().max(150),
  last_name: z.string().max(150),
  phone: z.string().max(32),
  tenant_name: z.string().max(255).optional(),
  tenant_phone: z.string().max(32).optional(),
  cpf_cnpj: z.string().optional(),
});

export type AccountSettingsFormValues = z.infer<typeof accountSettingsSchema>;

export function validateAccountSettings(
  data: AccountSettingsFormValues,
  opts: { isTenantAdmin: boolean; cpfCnpjEditable: boolean },
): string | null {
  if (opts.isTenantAdmin && data.tenant_name !== undefined && data.tenant_name.trim().length < 2) {
    return "Nome da empresa deve ter pelo menos 2 caracteres.";
  }
  if (opts.cpfCnpjEditable && data.cpf_cnpj) {
    const d = digitsOnly(data.cpf_cnpj);
    if (d && (d.length !== 11 && d.length !== 14)) {
      return "Informe CPF (11 dígitos) ou CNPJ (14 dígitos).";
    }
    if (d && !isValidCpfOrCnpj(data.cpf_cnpj)) {
      return "CPF ou CNPJ inválido.";
    }
  }
  const phoneDigits = digitsOnly(data.phone);
  if (phoneDigits && phoneDigits.length < 10) {
    return "Telefone inválido.";
  }
  return null;
}

const holderSchema = z.object({
  name: z.string().min(2, "Nome do titular obrigatório"),
  email: z.string().email("E-mail inválido"),
  cpfCnpj: z
    .string()
    .optional()
    .refine((v) => !v || isValidCpfOrCnpj(v), "CPF ou CNPJ inválido"),
  postalCode: z.string().refine((v) => digitsOnly(v).length === 8, "CEP deve ter 8 dígitos"),
  address: z.string().min(1, "Endereço obrigatório"),
  addressNumber: z.string().min(1, "Número obrigatório"),
  complement: z.string().optional(),
  province: z
    .string()
    .min(1, "Selecione a UF")
    .refine((s) => isValidUFSigla(s), "UF inválida"),
  phone: z.string().refine((v) => digitsOnly(v).length >= 10, "Telefone inválido"),
});

export const updateCardSchema = step3Schema.merge(holderSchema);

export type UpdateCardFormValues = z.infer<typeof updateCardSchema>;

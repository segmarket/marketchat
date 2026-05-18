import { z } from "zod";
import { isValidUFSigla } from "../../constants/brazilUF";
import { digitsOnly } from "../../utils/cpfCnpj";

export const marketFormSchema = z.object({
  name: z
    .string()
    .trim()
    .min(1, "Informe o nome do condomínio."),
  cep: z.string().refine((v) => digitsOnly(v).length === 8, "CEP deve ter 8 dígitos."),
  street: z.string().trim().min(1, "Informe a rua."),
  number: z.string().trim().min(1, "Informe o número."),
  complement: z.string().optional(),
  neighborhood: z.string().trim().min(1, "Informe o bairro."),
  city: z.string().trim().min(1, "Informe a cidade."),
  state: z
    .string()
    .min(1, "Selecione a UF.")
    .refine((s) => isValidUFSigla(s), "Selecione uma UF válida."),
  status: z.enum(["active", "inactive"]),
});

export type MarketFormValues = z.infer<typeof marketFormSchema>;

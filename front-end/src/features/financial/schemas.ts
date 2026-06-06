import { z } from "zod";
import type { PixKeyType } from "./types";

const pixKeyTypes = ["CPF", "CNPJ", "EMAIL", "PHONE", "RANDOM"] as const satisfies readonly PixKeyType[];

export const withdrawSchema = z.object({
  amount: z
    .string()
    .min(1, "Informe o valor do saque.")
    .refine((v) => {
      const n = Number.parseFloat(v.replace(",", "."));
      return !Number.isNaN(n) && n > 0;
    }, "Valor inválido."),
  pix_key_type: z.enum(pixKeyTypes),
  pix_key: z.string().min(1, "Informe a chave Pix."),
});

export type WithdrawFormValues = z.infer<typeof withdrawSchema>;

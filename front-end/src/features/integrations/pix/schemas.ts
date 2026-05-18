import { z } from "zod";
import { digitsOnly, isValidCpfOrCnpj } from "../../../utils/cpfCnpj";
import type { PixKeyType } from "./types";

const pixKeyTypeEnum = z.enum(["CPF", "CNPJ", "EMAIL", "PHONE", "RANDOM"]);

export const pixConfigFormSchema = z
  .object({
    name: z.string().trim().min(1, "Informe o nome do titular."),
    email: z.string().trim().email("Informe um e-mail válido."),
    cpf_cnpj: z
      .string()
      .min(1, "Informe CPF ou CNPJ.")
      .refine((v) => {
        const d = digitsOnly(v);
        return d.length === 11 || d.length === 14;
      }, "Informe CPF (11 dígitos) ou CNPJ (14 dígitos).")
      .refine((v) => isValidCpfOrCnpj(v), "CPF ou CNPJ inválido."),
    pix_key_type: pixKeyTypeEnum,
    pix_key: z.string().trim().min(1, "Informe a chave Pix."),
  })
  .superRefine((data, ctx) => {
    const key = data.pix_key.trim();
    const digits = digitsOnly(key);

    if (data.pix_key_type === "CPF") {
      if (digits.length !== 11 || !isValidCpfOrCnpj(digits)) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          message: "Chave Pix CPF inválida.",
          path: ["pix_key"],
        });
      }
    } else if (data.pix_key_type === "CNPJ") {
      if (digits.length !== 14 || !isValidCpfOrCnpj(digits)) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          message: "Chave Pix CNPJ inválida.",
          path: ["pix_key"],
        });
      }
    } else if (data.pix_key_type === "PHONE") {
      if (digits.length < 10 || digits.length > 11) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          message: "Informe um celular válido com DDD.",
          path: ["pix_key"],
        });
      }
    } else if (data.pix_key_type === "EMAIL") {
      if (!z.string().email().safeParse(key).success) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          message: "Informe um e-mail válido como chave Pix.",
          path: ["pix_key"],
        });
      }
    } else if (data.pix_key_type === "RANDOM") {
      const evp = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
      if (key.length < 32 && !evp.test(key)) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          message: "Informe uma chave aleatória válida (EVP).",
          path: ["pix_key"],
        });
      }
    }
  });

export type PixConfigFormValues = z.infer<typeof pixConfigFormSchema>;

export const PIX_KEY_TYPE_OPTIONS: { value: PixKeyType; label: string }[] = [
  { value: "CPF", label: "CPF" },
  { value: "CNPJ", label: "CNPJ" },
  { value: "EMAIL", label: "E-mail" },
  { value: "PHONE", label: "Celular" },
  { value: "RANDOM", label: "Chave aleatória" },
];

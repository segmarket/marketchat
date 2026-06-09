import { z } from "zod";
import { isValidUFSigla } from "../../constants/brazilUF";
import { digitsOnly, isValidCpfOrCnpj } from "../../utils/cpfCnpj";
import { isValidLuhn } from "../../utils/luhn";

export const step1Schema = z.object({
  fullName: z.string().min(3, "Informe seu nome completo"),
  email: z.string().email("E-mail inválido"),
  password: z.string().min(8, "Mínimo de 8 caracteres"),
  acceptTerms: z.literal(true, {
    errorMap: () => ({
      message: "Você precisa aceitar a Política de Privacidade e os Termos de Uso.",
    }),
  }),
});

export const step2Schema = z.object({
  company_name: z.string().min(2, "Nome da empresa obrigatório"),
  cpfCnpj: z
    .string()
    .min(1, "CPF ou CNPJ obrigatório")
    .refine((v) => {
      const d = digitsOnly(v);
      return d.length === 11 || d.length === 14;
    }, "Informe CPF (11 dígitos) ou CNPJ (14 dígitos)")
    .refine((v) => isValidCpfOrCnpj(v), "CPF ou CNPJ inválido"),
  phone: z.string().refine((v) => digitsOnly(v).length >= 10, "Digite um telefone com DDD."),
  cep: z.string().refine((v) => digitsOnly(v).length === 8, "CEP deve ter 8 dígitos"),
  address: z.string().min(1, "Informe o logradouro e cidade (ou preencha após o CEP)"),
  addressNumber: z.string().min(1, "Número obrigatório"),
  complement: z.string().optional(),
  province: z
    .string()
    .min(1, "Selecione a UF")
    .refine((s) => isValidUFSigla(s), "Selecione uma UF válida"),
});

export const step3Schema = z.object({
  cardNumber: z
    .string()
    .min(1, "Número do cartão obrigatório")
    .refine((v) => isValidLuhn(v), "Número do cartão inválido"),
  cardName: z.string().min(2, "Nome no cartão obrigatório"),
  cardExpiry: z
    .string()
    .regex(/^\d{2}\/\d{2}$/, "Use MM/AA")
    .refine((v) => {
      const [m, y] = v.split("/");
      const mm = parseInt(m!, 10);
      const yy = parseInt(y!, 10);
      if (mm < 1 || mm > 12) return false;
      const fullYear = yy >= 70 ? 1900 + yy : 2000 + yy;
      const expVal = fullYear * 12 + (mm - 1);
      const now = new Date();
      const nowVal = now.getFullYear() * 12 + now.getMonth();
      return expVal >= nowVal;
    }, "Data de validade inválida ou expirada"),
  cardCvv: z.string().regex(/^\d{3,4}$/, "CVV inválido"),
});

export type Step1Values = z.infer<typeof step1Schema>;
export type Step2Values = z.infer<typeof step2Schema>;
export type Step3Values = z.infer<typeof step3Schema>;

export const fullSignupSchema = step1Schema.merge(step2Schema).merge(step3Schema);
export type FullSignupValues = z.infer<typeof fullSignupSchema>;

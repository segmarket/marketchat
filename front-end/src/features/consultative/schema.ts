import { z } from "zod";
import { digitsOnly } from "../../utils/cpfCnpj";

export const consultativeLeadSchema = z.object({
  fullName: z.string().min(3, "Informe seu nome completo"),
  phone: z.string().refine((v) => digitsOnly(v).length >= 10, "Digite um telefone com DDD."),
  email: z.string().email("E-mail inválido"),
});

export type ConsultativeLeadValues = z.infer<typeof consultativeLeadSchema>;

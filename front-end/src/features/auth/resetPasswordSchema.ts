import { z } from "zod";

export const passwordResetRequestSchema = z.object({
  email: z.string().email("E-mail inválido"),
});

export type PasswordResetRequestValues = z.infer<typeof passwordResetRequestSchema>;

export const passwordResetConfirmSchema = z
  .object({
    new_password: z.string().min(8, "A senha deve ter pelo menos 8 caracteres"),
    new_password_confirm: z.string().min(1, "Confirme a senha"),
  })
  .refine((data) => data.new_password === data.new_password_confirm, {
    message: "As senhas não coincidem",
    path: ["new_password_confirm"],
  });

export type PasswordResetConfirmValues = z.infer<typeof passwordResetConfirmSchema>;

import { z } from "zod";

export const residentEditSchema = z.object({
  market_id: z.string().min(1, "Selecione um condomínio."),
});

export type ResidentEditFormValues = z.infer<typeof residentEditSchema>;

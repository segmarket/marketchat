import { api } from "../../../services/api";
import { digitsOnly } from "../../../utils/cpfCnpj";
import type { PixConfig, PixConfigFormValues } from "./types";

export async function fetchPixConfig(): Promise<PixConfig> {
  const { data } = await api.get<PixConfig>("/api/integrations/pix/");
  return data;
}

export async function savePixConfig(values: PixConfigFormValues): Promise<PixConfig> {
  const { data } = await api.put<PixConfig>("/api/integrations/pix/", {
    name: values.name.trim(),
    email: values.email.trim(),
    cpf_cnpj: digitsOnly(values.cpf_cnpj),
    pix_key_type: values.pix_key_type,
    pix_key:
      values.pix_key_type === "EMAIL"
        ? values.pix_key.trim()
        : values.pix_key_type === "RANDOM"
          ? values.pix_key.trim()
          : digitsOnly(values.pix_key),
  });
  return data;
}

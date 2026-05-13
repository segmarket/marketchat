import axios from "axios";

/** Extrai mensagem legível do corpo de erro típico do Django REST Framework. */
function flattenDrfErrors(data: unknown): string | null {
  if (!data || typeof data !== "object") return null;
  const d = data as Record<string, unknown>;

  const detail = d.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail) && detail.length > 0) {
    const first = detail[0];
    if (typeof first === "string") return first;
  }

  const lines: string[] = [];
  for (const [key, val] of Object.entries(d)) {
    if (key === "detail") continue;
    if (Array.isArray(val) && val[0] !== undefined) {
      lines.push(`${key}: ${String(val[0])}`);
    } else if (val && typeof val === "object" && !Array.isArray(val)) {
      for (const [k2, v2] of Object.entries(val as Record<string, unknown>)) {
        if (Array.isArray(v2) && v2[0] !== undefined) {
          lines.push(`${key}.${k2}: ${String(v2[0])}`);
        }
      }
    }
  }
  if (lines.length > 0) return lines.slice(0, 5).join(" · ");
  return null;
}

export type AxiosErrorMessageOptions = {
  /** Quando `err` não for um erro do axios */
  notAxiosMessage?: string;
  /** Quando houver status HTTP mas sem mensagem útil no corpo */
  genericHttpMessage?: string;
};

/**
 * Mensagem para toast / UI a partir de erro do axios (rede, 4xx/5xx, DRF).
 */
export function getAxiosErrorMessage(err: unknown, options?: AxiosErrorMessageOptions): string {
  if (!axios.isAxiosError(err)) {
    return (
      options?.notAxiosMessage ?? "Não foi possível concluir o cadastro. Verifique os dados."
    );
  }

  if (!err.response) {
    if (err.code === "ERR_NETWORK" || err.message === "Network Error") {
      return "Sem resposta do servidor. Confira se o Django está rodando e se VITE_API_BASE_URL no front aponta para a API (ex.: http://127.0.0.1:8000), sem barra no final.";
    }
    return err.message || "Falha de rede ou tempo esgotado.";
  }

  const fromBody = flattenDrfErrors(err.response.data);
  if (fromBody) return fromBody;

  const status = err.response.status;
  if (status === 404) {
    return "Rota da API não encontrada (404). O pedido provavelmente foi para o servidor do front (Vite), não para o Django: defina VITE_API_BASE_URL=http://127.0.0.1:8000 no .env do front ou, em desenvolvimento, deixe essa variável vazia e use o proxy do Vite (já configurado em vite.config.ts) com o Django rodando na porta 8000.";
  }
  return (
    options?.genericHttpMessage ??
    `Erro HTTP ${status}. Abra as ferramentas do navegador (Rede) e veja o corpo da resposta de /api/auth/register/.`
  );
}

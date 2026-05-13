/** Siglas das UFs brasileiras (inclui DF). */
export const BR_UF_SIGLAS = [
  "AC",
  "AL",
  "AP",
  "AM",
  "BA",
  "CE",
  "DF",
  "ES",
  "GO",
  "MA",
  "MT",
  "MS",
  "MG",
  "PA",
  "PB",
  "PR",
  "PE",
  "PI",
  "RJ",
  "RN",
  "RS",
  "RO",
  "RR",
  "SC",
  "SP",
  "SE",
  "TO",
] as const;

export type UFSigla = (typeof BR_UF_SIGLAS)[number];

/** Opções para `<select>` (somente sigla, ordenado alfabeticamente). */
export const UF_SELECT_OPTIONS: { value: UFSigla; label: string }[] = [...BR_UF_SIGLAS]
  .map((sigla) => ({
    value: sigla,
    label: sigla,
  }))
  .sort((a, b) => a.value.localeCompare(b.value, "pt-BR"));

export function isValidUFSigla(s: string): boolean {
  return (BR_UF_SIGLAS as readonly string[]).includes(s);
}

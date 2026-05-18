import { digitsOnly } from "../../utils/cpfCnpj";

export type MarketAddressParts = {
  cep: string;
  street: string;
  number: string;
  complement: string;
  neighborhood: string;
  city: string;
  state: string;
};

const EMPTY_ADDRESS: MarketAddressParts = {
  cep: "",
  street: "",
  number: "",
  complement: "",
  neighborhood: "",
  city: "",
  state: "",
};

function formatCepDisplay(cep: string): string {
  const d = digitsOnly(cep);
  if (d.length !== 8) return cep;
  return `${d.slice(0, 5)}-${d.slice(5)}`;
}

export function formatMarketAddressForApi(parts: MarketAddressParts): string {
  return JSON.stringify({
    cep: digitsOnly(parts.cep),
    street: parts.street.trim(),
    number: parts.number.trim(),
    complement: parts.complement.trim(),
    neighborhood: parts.neighborhood.trim(),
    city: parts.city.trim(),
    state: parts.state.trim().toUpperCase(),
  });
}

export function parseMarketAddress(stored: string): MarketAddressParts {
  if (!stored.trim()) return { ...EMPTY_ADDRESS };

  try {
    const data = JSON.parse(stored) as Partial<MarketAddressParts>;
    if (data && typeof data === "object" && typeof data.street === "string") {
      return {
        cep: data.cep ? formatCepDisplay(String(data.cep)) : "",
        street: data.street ?? "",
        number: data.number ?? "",
        complement: data.complement ?? "",
        neighborhood: data.neighborhood ?? "",
        city: data.city ?? "",
        state: data.state ?? "",
      };
    }
  } catch {
    /* legado: texto livre no campo address */
  }

  return { ...EMPTY_ADDRESS, street: stored };
}

export function formatMarketAddressDisplay(stored: string): string {
  const parts = parseMarketAddress(stored);
  const hasStructured =
    parts.street &&
    (parts.number || parts.neighborhood || parts.city || digitsOnly(parts.cep).length === 8);

  if (!hasStructured) {
    return stored.trim() || "—";
  }

  const line1 = [parts.street, parts.number].filter(Boolean).join(", ");
  const line2 = [parts.neighborhood, [parts.city, parts.state].filter(Boolean).join(" - ")]
    .filter(Boolean)
    .join(" — ");
  const cep = digitsOnly(parts.cep).length === 8 ? `CEP ${formatCepDisplay(parts.cep)}` : "";

  return [line1, parts.complement, line2, cep].filter(Boolean).join(" · ");
}

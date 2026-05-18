import { api } from "../../services/api";
import type { MarketsSearchFilters } from "./searchTypes";
import type { Market, MarketCreatePayload, MarketUpdatePayload } from "./types";

export type FetchMarketsParams = {
  name?: string;
  address?: string;
  status?: string;
};

export function buildMarketsQueryParams(
  filters?: Partial<MarketsSearchFilters>,
): FetchMarketsParams | undefined {
  if (!filters) return undefined;
  const params: FetchMarketsParams = {};
  const name = filters.name?.trim();
  const address = filters.address?.trim();
  if (name) params.name = name;
  if (address) params.address = address;
  if (filters.status === "active" || filters.status === "inactive") {
    params.status = filters.status;
  }
  return Object.keys(params).length ? params : undefined;
}

export async function fetchMarkets(params?: FetchMarketsParams): Promise<Market[]> {
  const query: Record<string, string> = {};
  if (params?.name) query.name = params.name;
  if (params?.address) query.address = params.address;
  if (params?.status) query.status = params.status;
  const { data } = await api.get<Market[]>("/api/markets/", {
    params: Object.keys(query).length ? query : undefined,
  });
  return data;
}

export async function createMarket(payload: MarketCreatePayload): Promise<Market> {
  const { data } = await api.post<Market>("/api/markets/", payload);
  return data;
}

export async function updateMarket(id: number, payload: MarketUpdatePayload): Promise<Market> {
  const { data } = await api.patch<Market>(`/api/markets/${id}/`, payload);
  return data;
}

export async function deleteMarket(id: number): Promise<void> {
  await api.delete(`/api/markets/${id}/`);
}

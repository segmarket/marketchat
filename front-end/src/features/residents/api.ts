import { api } from "../../services/api";
import { digitsOnly } from "./format";
import type { ResidentsSearchFilters } from "./searchTypes";
import type { Resident, ResidentMarketOption } from "./types";

export type FetchResidentsParams = {
  marketId?: number;
  name?: string;
  phone?: string;
};

export function buildResidentsQueryParams(
  filters?: Partial<ResidentsSearchFilters>,
): FetchResidentsParams | undefined {
  if (!filters) return undefined;
  const name = filters.name?.trim();
  const phone = digitsOnly(filters.phone ?? "");
  const marketId = filters.marketId ? Number.parseInt(filters.marketId, 10) : undefined;
  const params: FetchResidentsParams = {};
  if (name) params.name = name;
  if (phone) params.phone = phone;
  if (marketId && Number.isFinite(marketId)) params.marketId = marketId;
  return Object.keys(params).length ? params : undefined;
}

export async function fetchResidents(params?: FetchResidentsParams): Promise<Resident[]> {
  const query: Record<string, string | number> = {};
  if (params?.marketId) query.market_id = params.marketId;
  if (params?.name) query.name = params.name;
  if (params?.phone) query.phone = params.phone;
  const { data } = await api.get<Resident[]>("/api/residents/", {
    params: Object.keys(query).length ? query : undefined,
  });
  return data;
}

export async function fetchResidentMarkets(): Promise<ResidentMarketOption[]> {
  const { data } = await api.get<ResidentMarketOption[]>("/api/residents/markets/");
  return data;
}

export async function patchResidentMarket(
  residentId: number,
  marketId: number,
): Promise<Resident> {
  const { data } = await api.patch<Resident>(`/api/residents/${residentId}/`, {
    market_id: marketId,
  });
  return data;
}

export async function deleteResident(residentId: number): Promise<void> {
  await api.delete(`/api/residents/${residentId}/`);
}

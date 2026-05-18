import type { CartStatus } from "./types";

export type SalesSearchFilters = {
  residentName: string;
  marketId: string;
  status: CartStatus;
  dateFrom: string;
  dateTo: string;
};

export function emptySalesSearchFilters(): SalesSearchFilters {
  return {
    residentName: "",
    marketId: "",
    status: "",
    dateFrom: "",
    dateTo: "",
  };
}

export function hasActiveSalesFilters(filters: SalesSearchFilters): boolean {
  return Boolean(
    filters.residentName.trim()
      || filters.marketId
      || filters.status
      || filters.dateFrom
      || filters.dateTo,
  );
}

export function buildSalesQueryParams(
  filters: SalesSearchFilters,
  page: number,
): Record<string, string | number> {
  const params: Record<string, string | number> = { page };
  const name = filters.residentName.trim();
  if (name) params.resident_name = name;
  if (filters.marketId) params.market_id = filters.marketId;
  if (filters.status) params.status = filters.status;
  if (filters.dateFrom) params.date_from = filters.dateFrom;
  if (filters.dateTo) params.date_to = filters.dateTo;
  return params;
}

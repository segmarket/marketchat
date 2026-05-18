export type MarketsSearchFilters = {
  name: string;
  address: string;
  status: string;
};

export const emptyMarketsSearchFilters = (): MarketsSearchFilters => ({
  name: "",
  address: "",
  status: "",
});

export function hasActiveMarketsFilters(filters: MarketsSearchFilters): boolean {
  return Boolean(filters.name.trim() || filters.address.trim() || filters.status);
}

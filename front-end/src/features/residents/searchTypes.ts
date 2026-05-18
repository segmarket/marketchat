import { digitsOnly } from "./format";

export type ResidentsSearchFilters = {
  name: string;
  phone: string;
  marketId: string;
};

export const emptyResidentsSearchFilters = (): ResidentsSearchFilters => ({
  name: "",
  phone: "",
  marketId: "",
});

export function hasActiveResidentsFilters(filters: ResidentsSearchFilters): boolean {
  return Boolean(filters.name.trim() || digitsOnly(filters.phone) || filters.marketId);
}

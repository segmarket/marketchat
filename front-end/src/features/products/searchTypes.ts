export type ProductsSearchFilters = {
  name: string;
  sku: string;
  status: string;
};

export const emptyProductsSearchFilters = (): ProductsSearchFilters => ({
  name: "",
  sku: "",
  status: "",
});

export function hasActiveProductsFilters(filters: ProductsSearchFilters): boolean {
  return Boolean(filters.name.trim() || filters.sku.trim() || filters.status);
}

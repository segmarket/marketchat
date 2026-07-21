import { api } from "../../services/api";
import type { ProductsSearchFilters } from "./searchTypes";
import type {
  ImportConfirmResponse,
  ImportPreviewResponse,
  Product,
  ProductPatchPayload,
} from "./types";

export type FetchProductsParams = {
  name?: string;
  sku?: string;
  status?: string;
};

export function buildProductsQueryParams(
  filters?: Partial<ProductsSearchFilters>,
): FetchProductsParams | undefined {
  if (!filters) return undefined;
  const params: FetchProductsParams = {};
  const name = filters.name?.trim();
  const sku = filters.sku?.trim();
  if (name) params.name = name;
  if (sku) params.sku = sku;
  if (filters.status === "active" || filters.status === "inactive") {
    params.status = filters.status;
  }
  return Object.keys(params).length ? params : undefined;
}

export async function fetchProducts(params?: FetchProductsParams): Promise<Product[]> {
  const query: Record<string, string> = {};
  if (params?.name) query.name = params.name;
  if (params?.sku) query.sku = params.sku;
  if (params?.status) query.status = params.status;
  const { data } = await api.get<Product[]>("/api/products/", {
    params: Object.keys(query).length ? query : undefined,
  });
  return data;
}

export type ProductSearchHit = {
  id: number;
  name: string;
  price: string;
};

export async function searchProducts(q: string): Promise<ProductSearchHit[]> {
  const trimmed = q.trim();
  if (trimmed.length < 2) return [];
  const { data } = await api.get<ProductSearchHit[]>("/api/products/search/", {
    params: { q: trimmed },
  });
  return data;
}

export async function patchProduct(id: number, payload: ProductPatchPayload): Promise<Product> {
  const { data } = await api.patch<Product>(`/api/products/${id}/`, payload);
  return data;
}

export async function downloadProductsTemplate(): Promise<void> {
  const { data } = await api.get<Blob>("/api/products/download-template/", {
    responseType: "blob",
  });
  const url = window.URL.createObjectURL(data);
  const link = document.createElement("a");
  link.href = url;
  link.download = "produtos-modelo.xlsx";
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(url);
}

export async function uploadProductsPreview(file: File): Promise<ImportPreviewResponse> {
  const formData = new FormData();
  formData.append("file", file);
  const { data } = await api.post<ImportPreviewResponse>(
    "/api/products/upload-preview/",
    formData,
    {
      headers: { "Content-Type": "multipart/form-data" },
    },
  );
  return data;
}

export async function confirmProductsImport(
  importToken: string,
): Promise<ImportConfirmResponse> {
  const { data } = await api.post<ImportConfirmResponse>("/api/products/upload-confirm/", {
    import_token: importToken,
  });
  return data;
}

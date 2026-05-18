export type ProductStatus = "active" | "inactive";

export type Product = {
  id: number;
  sku: string;
  name: string;
  search_aliases: string;
  price: string;
  status: ProductStatus;
  created_at?: string;
  updated_at?: string;
};

export type ProductPatchPayload = {
  name?: string;
  search_aliases?: string;
  price?: string | number;
  status?: ProductStatus;
};

export type ImportPreviewResponse = {
  new_count: number;
  updated_count: number;
  import_token: string;
};

export type ImportConfirmResponse = {
  created: number;
  updated: number;
  import_token: string;
};

import { api } from "../../services/api";
import type { CartDetail, SalesDashboardResponse } from "./types";

export async function fetchSalesDashboard(
  params: Record<string, string | number>,
): Promise<SalesDashboardResponse> {
  const { data } = await api.get<SalesDashboardResponse>("/api/sales/dashboard/", {
    params,
  });
  return data;
}

export async function fetchCartDetail(cartId: number): Promise<CartDetail> {
  const { data } = await api.get<CartDetail>(`/api/sales/carts/${cartId}/`);
  return data;
}

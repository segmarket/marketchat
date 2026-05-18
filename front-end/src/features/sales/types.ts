export type CartStatus =
  | "OPEN"
  | "AWAITING_PHOTO"
  | "AWAITING_PAYMENT"
  | "COMPLETED"
  | "EXPIRED"
  | "CANCELLED"
  | "";

export type SalesMetrics = {
  total_revenue: string;
  total_orders: number;
  average_ticket: string;
  conversion_rate: number;
  abandoned_orders: number;
};

export type SalesOrderRow = {
  id: number;
  resident_name: string;
  market_name: string;
  total_value: string;
  status: string;
  created_at: string;
  asaas_billing_id: string;
  security_photo_url: string;
};

export type SalesDashboardResponse = {
  metrics: SalesMetrics;
  orders: {
    count: number;
    next: number | null;
    previous: number | null;
    results: SalesOrderRow[];
  };
};

export type CartItemDetail = {
  product_name: string;
  sku: string;
  quantity: number;
  unit_price: string;
  subtotal: string;
  product_image_url: string | null;
};

export type CartDetail = {
  id: number;
  resident_name: string;
  resident_phone: string;
  market_name: string;
  status: string;
  total_value: string;
  created_at: string;
  updated_at: string;
  asaas_billing_id: string;
  security_photo_url: string;
  items: CartItemDetail[];
};

export type SalesMarketOption = {
  id: number;
  name: string;
};

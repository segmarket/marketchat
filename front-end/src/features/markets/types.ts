export type MarketStatus = "active" | "inactive";

export type Market = {
  id: number;
  name: string;
  address: string;
  status: MarketStatus;
  created_at: string;
  updated_at: string;
};

export type MarketCreatePayload = {
  name: string;
  address: string;
  status: MarketStatus;
};

export type MarketUpdatePayload = Partial<MarketCreatePayload>;

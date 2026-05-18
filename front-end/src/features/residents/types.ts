export type ResidentMarket = {
  id: number;
  name: string;
};

export type Resident = {
  id: number;
  name: string;
  phone_number: string;
  market: ResidentMarket | null;
  created_at: string;
};

export type ResidentMarketOption = {
  id: number;
  name: string;
};

export type PixKeyType = "CPF" | "CNPJ" | "EMAIL" | "PHONE" | "RANDOM";

export type LedgerEntryType = "INFLOW" | "OUTFLOW";

export type LedgerRow = {
  id: number;
  amount: string;
  signed_amount: string;
  entry_type: LedgerEntryType;
  entry_type_label: string;
  description: string;
  external_id: string;
  created_at: string;
};

export type FinancialStatement = {
  balance_available: string;
  balance_blocked: string;
  balance_processing: string;
  fee_percent: number;
  default_pix_key: string;
  default_pix_key_type: PixKeyType | "";
  has_pix_key_configured: boolean;
  page: number;
  total_count: number;
  next: number | null;
  previous: number | null;
  results: LedgerRow[];
};

export type WithdrawPayload = {
  amount: string;
};

export type WalletSettingsPayload = {
  default_pix_key_type: PixKeyType;
  default_pix_key: string;
};

export type WalletSettings = {
  default_pix_key: string;
  default_pix_key_type: PixKeyType | "";
  default_pix_key_masked: string;
  has_pix_key_configured: boolean;
};

export type WithdrawResponse = {
  withdrawal_id: number;
  status: string;
  message: string;
};

export type PixKeyType = "CPF" | "CNPJ" | "EMAIL" | "PHONE" | "RANDOM";

export type AccountStatus = "PENDING" | "APPROVED" | "REJECTED";

export type PixPrefill = {
  name: string;
  email: string;
  cpf_cnpj: string;
};

export type AsaasKycStatus =
  | "PENDING"
  | "APPROVED"
  | "REJECTED"
  | "AWAITING_APPROVAL"
  | "NOT_SENT"
  | "";

export type PixConfig = {
  name: string;
  email: string;
  cpf_cnpj: string;
  pix_key_type: PixKeyType;
  pix_key: string;
  asaas_wallet_id: string;
  account_status: AccountStatus;
  has_wallet: boolean;
  has_market_address: boolean;
  can_manage: boolean;
  prefill: PixPrefill;
  asaas_account_id?: string;
  asaas_status_general?: AsaasKycStatus;
  asaas_status_commercial?: AsaasKycStatus;
  asaas_status_documentation?: AsaasKycStatus;
  asaas_status_bank?: AsaasKycStatus;
  status_message?: string;
  status_synced_at?: string | null;
  split_ready?: boolean;
  can_sync_status?: boolean;
};

export type PixConfigFormValues = {
  name: string;
  email: string;
  cpf_cnpj: string;
  pix_key_type: PixKeyType;
  pix_key: string;
};

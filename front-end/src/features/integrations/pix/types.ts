export type PixKeyType = "CPF" | "CNPJ" | "EMAIL" | "PHONE" | "RANDOM";

export type AccountStatus = "PENDING" | "APPROVED" | "REJECTED";

export type PixPrefill = {
  name: string;
  email: string;
  cpf_cnpj: string;
};

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
};

export type PixConfigFormValues = {
  name: string;
  email: string;
  cpf_cnpj: string;
  pix_key_type: PixKeyType;
  pix_key: string;
};

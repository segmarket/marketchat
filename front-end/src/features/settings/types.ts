export type InvoiceStatus = "PAID" | "PENDING" | "OVERDUE";

export type AccountSettingsUser = {
  id: number;
  email: string;
  first_name: string;
  last_name: string;
  phone: string;
  is_tenant_admin: boolean;
  can_manage_integrations: boolean;
  is_platform_superuser: boolean;
  has_tenant: boolean;
};

export type AccountSettingsTenant = {
  id: number;
  name: string;
  slug: string;
  phone: string;
  cpf_cnpj: string;
  cpf_cnpj_editable: boolean;
};

export type AccountSettingsResponse = {
  user: AccountSettingsUser;
  tenant: AccountSettingsTenant | null;
};

export type AccountSettingsPatch = {
  first_name?: string;
  last_name?: string;
  phone?: string;
  tenant_name?: string;
  tenant_phone?: string;
  cpf_cnpj?: string;
};

export type BillingHistoryItem = {
  due_date: string;
  value: number;
  status: InvoiceStatus;
  billing_type: string;
  invoice_url: string;
};

export type BillingHistoryResponse = {
  results: BillingHistoryItem[];
};

export type TenantSubscriptionStatus =
  | "TRIAL"
  | "ACTIVE"
  | "OVERDUE"
  | "SUSPENDED"
  | "CANCELED";

export type PaymentMethodSummary = {
  billing_type: string;
  card_brand: string | null;
  card_last_four: string | null;
  display_label: string;
  next_due_date?: string | null;
  asaas_status?: string;
  subscription_status?: TenantSubscriptionStatus;
  subscription_canceled?: boolean;
  can_cancel?: boolean;
  can_reactivate?: boolean;
  in_trial_period?: boolean;
  trial_ends_at?: string;
  active_markets_count?: number;
  monthly_total?: number;
  unit_price?: number;
  is_in_grace_period?: boolean;
};

export type SettingsTabId = "account" | "plan" | "history";

export type SettingsSectionId =
  | "account"
  | "markets"
  | "integrations"
  | "privacy"
  | "plan"
  | "history";

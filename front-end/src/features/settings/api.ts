import { api } from "../../services/api";
import type {
  AccountSettingsPatch,
  AccountSettingsResponse,
  BillingHistoryResponse,
  BotScheduleDay,
  BotScheduleResponse,
  PaymentMethodSummary,
  RegularizeResponse,
} from "./types";

export async function fetchAccountSettings(): Promise<AccountSettingsResponse> {
  const { data } = await api.get<AccountSettingsResponse>("/api/settings/account/");
  return data;
}

export async function patchAccountSettings(
  payload: AccountSettingsPatch,
): Promise<AccountSettingsResponse> {
  const { data } = await api.patch<AccountSettingsResponse>("/api/settings/account/", payload);
  return data;
}

export async function fetchBotSchedule(): Promise<BotScheduleResponse> {
  const { data } = await api.get<BotScheduleResponse>("/api/settings/bot-schedule/");
  return data;
}

export async function saveBotSchedule(
  days: BotScheduleDay[],
): Promise<BotScheduleResponse> {
  const { data } = await api.put<BotScheduleResponse>("/api/settings/bot-schedule/", {
    days,
  });
  return data;
}

export async function patchBotGlobalActive(
  isBotActiveGlobal: boolean,
): Promise<BotScheduleResponse> {
  const { data } = await api.patch<BotScheduleResponse>("/api/settings/bot-schedule/", {
    is_bot_active_global: isBotActiveGlobal,
  });
  return data;
}

export async function fetchBillingHistory(): Promise<BillingHistoryResponse> {
  const { data } = await api.get<BillingHistoryResponse>("/api/settings/billing/history/");
  return data;
}

export async function fetchPaymentMethod(): Promise<PaymentMethodSummary> {
  const { data } = await api.get<PaymentMethodSummary>("/api/settings/billing/payment-method/");
  return data;
}

export type UpdateCardPayload = {
  credit_card: {
    holderName: string;
    number: string;
    expiryMonth: string;
    expiryYear: string;
    ccv: string;
  };
  credit_card_holder: {
    name: string;
    email: string;
    cpfCnpj?: string;
    postalCode: string;
    address: string;
    addressNumber: string;
    complement?: string;
    province: string;
    phone: string;
  };
};

export async function updatePaymentMethod(
  payload: UpdateCardPayload,
): Promise<PaymentMethodSummary> {
  const { data } = await api.post<PaymentMethodSummary>(
    "/api/settings/billing/payment-method/",
    payload,
  );
  return data;
}

/** Paga agora, com o cartão informado, a(s) fatura(s) em aberto; o acesso só volta com a confirmação. */
export async function regularizeWithCard(payload: UpdateCardPayload): Promise<RegularizeResponse> {
  const { data } = await api.post<RegularizeResponse>("/api/settings/billing/regularize/", payload);
  return data;
}

export async function cancelSubscription(): Promise<{ detail: string }> {
  const { data } = await api.post<{ detail: string }>(
    "/api/settings/billing/subscription/cancel/",
  );
  return data;
}

export async function reactivateSubscription(): Promise<PaymentMethodSummary & { detail: string }> {
  const { data } = await api.post<PaymentMethodSummary & { detail: string }>(
    "/api/settings/billing/subscription/reactivate/",
  );
  return data;
}

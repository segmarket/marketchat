import { api } from "../../services/api";
import type {
  FinancialStatement,
  WalletSettings,
  WalletSettingsPayload,
  WithdrawPayload,
  WithdrawResponse,
} from "./types";

export async function fetchFinancialStatement(page = 1): Promise<FinancialStatement> {
  const { data } = await api.get<FinancialStatement>("/api/financial/statement/", {
    params: { page },
  });
  return data;
}

export async function requestWithdraw(payload: WithdrawPayload): Promise<WithdrawResponse> {
  const { data } = await api.post<WithdrawResponse>("/api/financial/withdraw/", payload);
  return data;
}

export async function fetchWalletSettings(): Promise<WalletSettings> {
  const { data } = await api.get<WalletSettings>("/api/financial/wallet/settings/");
  return data;
}

export async function updateWalletSettings(payload: WalletSettingsPayload): Promise<WalletSettings> {
  const { data } = await api.patch<WalletSettings>("/api/financial/wallet/settings/", payload);
  return data;
}

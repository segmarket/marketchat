import { api } from "../../services/api";
import type { WhatsappDashboard, WhatsappIntegrationState } from "./types";

export async function fetchWhatsappIntegration(): Promise<WhatsappDashboard> {
  const { data } = await api.get<WhatsappDashboard>("/api/integrations/whatsapp/");
  return data;
}

export async function provisionWhatsapp(pairPhone?: string): Promise<WhatsappDashboard> {
  const { data } = await api.post<WhatsappDashboard>(
    "/api/integrations/whatsapp/provision/",
    pairPhone ? { pair_phone: pairPhone } : {},
  );
  return data;
}

export async function fetchWhatsappQrcode(): Promise<WhatsappDashboard> {
  const { data } = await api.get<WhatsappDashboard>("/api/integrations/whatsapp/qrcode/");
  return data;
}

export async function fetchWhatsappStatus(): Promise<WhatsappDashboard> {
  const { data } = await api.get<WhatsappDashboard>("/api/integrations/whatsapp/status/");
  return data;
}

export async function refreshWhatsappAvatar(): Promise<WhatsappDashboard> {
  const { data } = await api.post<WhatsappDashboard>(
    "/api/integrations/whatsapp/avatar/refresh/",
    {},
  );
  return data;
}

export async function restartWhatsapp(): Promise<WhatsappDashboard> {
  const { data } = await api.post<WhatsappDashboard>(
    "/api/integrations/whatsapp/restart/",
    {},
  );
  return data;
}

export async function disconnectWhatsapp(): Promise<WhatsappIntegrationState> {
  const { data } = await api.post<WhatsappIntegrationState>(
    "/api/integrations/whatsapp/disconnect/",
    {},
  );
  return data;
}

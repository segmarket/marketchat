export type IntegrationsTabId = "whatsapp" | "pix";

export type WhatsappConnectionStatus = "unknown" | "connecting" | "open" | "close";

export type HealthStatus = "ok" | "error" | "unknown";

export type WhatsappPlatform = "android" | "ios" | "unknown";

export type WhatsappIntegrationState = {
  has_instance: boolean;
  instance_name: string;
  connection_status: WhatsappConnectionStatus;
  connected: boolean;
  is_active: boolean;
  pair_phone: string;
  updated_at: string | null;
  qrcode_image?: string;
  profile_name: string;
  profile_picture_url: string;
  phone_number: string;
  platform: WhatsappPlatform;
  disconnect_reason: string;
  session_expired: boolean;
  evolution_api_status: HealthStatus;
  webhook_status: HealthStatus;
  can_manage_integrations?: boolean;
  is_platform_superuser?: boolean;
  has_tenant?: boolean;
};

export type WhatsappDashboard = WhatsappIntegrationState;

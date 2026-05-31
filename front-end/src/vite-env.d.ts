/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_BASE_URL: string;
  readonly VITE_DEV_API_PORT?: string;
  readonly VITE_TRIAL_SUBSCRIPTION_PRICE?: string;
  readonly VITE_MARKETING_ORIGIN?: string;
  readonly VITE_FB_APP_ID?: string;
  readonly VITE_GTM_ID?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}

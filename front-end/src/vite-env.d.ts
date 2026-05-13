/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_BASE_URL: string;
  readonly VITE_TRIAL_SUBSCRIPTION_PRICE?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}

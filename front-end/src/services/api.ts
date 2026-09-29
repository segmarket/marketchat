import axios, { type InternalAxiosRequestConfig } from "axios";

/**
 * Base da API.
 * Staging (Opção A): app em staging-app, Django em staging-api — usa VITE_API_BASE_URL.
 * Alternativa: ProxyPass /api no vhost do app e VITE_API_BASE_URL=https://staging-app...
 */
export function resolveApiBaseUrl(): string {
  if (import.meta.env.DEV) return "";

  const fromEnv = (import.meta.env.VITE_API_BASE_URL as string | undefined)?.trim();
  if (fromEnv) return fromEnv.replace(/\/$/, "");

  if (typeof window !== "undefined") {
    const host = window.location.hostname.toLowerCase();
    if (
      host === "staging-app.marketchat.com.br" ||
      host === "staging.marketchat.com.br"
    ) {
      return "https://staging-api.marketchat.com.br";
    }
  }

  return "";
}

const baseURL = resolveApiBaseUrl();

export const api = axios.create({
  baseURL,
  headers: { "Content-Type": "application/json" },
});

const ACCESS_KEY = "access_token";
const REFRESH_KEY = "refresh_token";

export function getAccessToken(): string | null {
  return localStorage.getItem(ACCESS_KEY);
}

export function setTokens(access: string, refresh: string): void {
  localStorage.setItem(ACCESS_KEY, access);
  localStorage.setItem(REFRESH_KEY, refresh);
}

export function clearTokens(): void {
  localStorage.removeItem(ACCESS_KEY);
  localStorage.removeItem(REFRESH_KEY);
}

export function getRefreshToken(): string | null {
  return localStorage.getItem(REFRESH_KEY);
}

function shouldSkip401Redirect(config: InternalAxiosRequestConfig | undefined): boolean {
  if (!config?.url) return false;
  const u = config.url.toLowerCase();
  const method = (config.method ?? "get").toLowerCase();
  if (method === "post" && u.includes("/auth/token") && !u.includes("/refresh")) return true;
  if (method === "post" && u.includes("/auth/register")) return true;
  if (method === "post" && u.includes("/auth/password")) return true;
  return false;
}

api.interceptors.request.use((config) => {
  const token = getAccessToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    const status = error.response?.status as number | undefined;
    const cfg = error.config as InternalAxiosRequestConfig | undefined;

    if (status === 401 && !shouldSkip401Redirect(cfg)) {
      clearTokens();
      const path = window.location.pathname;
      if (
        !path.startsWith("/signin") &&
        !path.startsWith("/login") &&
        !path.startsWith("/auth/") &&
        !path.startsWith("/reset-password")
      ) {
        window.location.assign("/signin");
      }
    }

    if (status === 402) {
      const errorCode = error.response?.data?.error as string | undefined;
      const path = window.location.pathname;
      if (errorCode === "trial_expired") {
        if (!path.startsWith("/admin/trial-expired") && !path.startsWith("/admin/settings")) {
          window.location.assign("/admin/trial-expired");
        }
      } else if (
        errorCode === "billing_suspended" &&
        !path.startsWith("/admin/billing-blocked") &&
        !path.startsWith("/admin/settings")
      ) {
        window.location.assign("/admin/billing-blocked");
      } else if (!path.startsWith("/admin/settings")) {
        window.location.assign("/admin/settings?tab=plan");
      }
    }

    return Promise.reject(error);
  },
);

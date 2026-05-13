import axios, { type InternalAxiosRequestConfig } from "axios";

const envUrl = (import.meta.env.VITE_API_BASE_URL as string | undefined)?.trim();
/** Em dev, URL vazia + proxy no Vite (vite.config.ts) encaminha /api para o Django. */
const baseURL = envUrl || (import.meta.env.DEV ? "" : "");

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
        !path.startsWith("/login") &&
        !path.startsWith("/auth/") &&
        !path.startsWith("/reset-password")
      ) {
        window.location.assign("/login");
      }
    }

    if (status === 402) {
      if (!window.location.pathname.startsWith("/admin/billing")) {
        window.location.assign("/admin/billing");
      }
    }

    return Promise.reject(error);
  },
);

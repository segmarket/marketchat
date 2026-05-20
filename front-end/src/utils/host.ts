const PRODUCTION_APP_ORIGIN = "https://app.marketchat.com.br";
const STAGING_APP_ORIGIN = "https://staging-app.marketchat.com.br";

/** Corrige VITE_APP_ORIGIN legado (staging.app.* quebra SSL no Cloudflare). */
export function normalizeAppOrigin(origin: string): string {
  const trimmed = origin.trim().replace(/\/$/, "");
  if (!trimmed) return trimmed;
  try {
    const url = new URL(trimmed);
    if (url.hostname.includes("staging.app.")) {
      url.hostname = url.hostname.replace("staging.app.", "staging-app.");
      return url.origin;
    }
  } catch {
    return trimmed.replace(/staging\.app\./g, "staging-app.");
  }
  return trimmed;
}

function normalizePath(path: string): string {
  return path.startsWith("/") ? path : `/${path}`;
}

/**
 * Origem do painel (app) conforme o hostname da landing/marketing.
 * Ignora VITE_APP_ORIGIN em staging para evitar staging.app.* (SSL Cloudflare).
 */
export function resolveAppOrigin(hostname = window.location.hostname): string {
  const host = hostname.toLowerCase();

  // staging.app.* → sempre staging-app.* (hífen, sem subdomínio aninhado)
  if (host.includes("staging.app.") || host === "staging.app.marketchat.com.br") {
    return STAGING_APP_ORIGIN;
  }

  if (host.includes("staging")) {
    return STAGING_APP_ORIGIN;
  }

  if (host === "localhost" || host === "127.0.0.1") {
    const port = typeof window !== "undefined" && window.location.port ? window.location.port : "5173";
    return `http://app.localhost:${port}`;
  }

  if (host === "app.localhost") {
    const port = typeof window !== "undefined" && window.location.port ? window.location.port : "5173";
    return `http://app.localhost:${port}`;
  }

  if (host.endsWith(".localhost") && !host.startsWith("app.")) {
    const port = typeof window !== "undefined" && window.location.port ? window.location.port : "5173";
    return `http://app.localhost:${port}`;
  }

  return PRODUCTION_APP_ORIGIN;
}

/** URL completa do painel (padrão: login em /signin). */
export function getAppUrl(path = "/signin", hostname = window.location.hostname): string {
  return `${resolveAppOrigin(hostname)}${normalizePath(path)}`;
}

export function getAppSignInUrl(): string {
  return getAppUrl("/signin");
}

export function getAppRegisterUrl(): string {
  return getAppUrl("/register");
}

export function isAppHost(hostname = window.location.hostname): boolean {
  const host = hostname.toLowerCase();
  return (
    host === "app.marketchat.com.br" ||
    host === "staging-app.marketchat.com.br" ||
    host === "app.localhost" ||
    host.startsWith("app.")
  );
}

export function getAppOrigin(): string {
  const host = window.location.hostname.toLowerCase();

  if (host.includes("staging")) {
    return STAGING_APP_ORIGIN;
  }

  const fromEnv = import.meta.env.VITE_APP_ORIGIN?.trim();
  if (fromEnv) {
    return normalizeAppOrigin(fromEnv);
  }

  return resolveAppOrigin();
}

/** @deprecated Prefer {@link getAppUrl} nos CTAs públicos. */
export function appUrl(path: string): string {
  return getAppUrl(path);
}

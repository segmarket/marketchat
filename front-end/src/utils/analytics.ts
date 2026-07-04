import {
  hasAnalyticsConsent,
  hasMarketingConsent,
} from "../features/marketing/cookieConsent";
import { isAppHost } from "./host";

declare global {
  interface Window {
    dataLayer?: Record<string, unknown>[];
  }
}

const GTM_SCRIPT_ID = "marketchat-gtm-script";
const GTM_NOSCRIPT_ID = "marketchat-gtm-noscript";

let consentDefaultsInitialized = false;

function ensureDataLayer(): Record<string, unknown>[] {
  window.dataLayer = window.dataLayer || [];
  return window.dataLayer;
}

function canTrackEvents(): boolean {
  if (isAppHost()) {
    return hasMarketingConsent() || hasAnalyticsConsent();
  }
  return hasMarketingConsent();
}

/**
 * Emite evento apenas no dataLayer (GTM). Tags Meta Pixel / GA4 ficam no container GTM.
 * Não envie PII em claro (e-mail, telefone, CPF, senha). Hashes SHA-256
 * (`hashed_email` / `hashed_phone`) são ok para Advanced Matching via GTM.
 */
export function trackEvent(eventName: string, eventData?: Record<string, unknown>): void {
  try {
    if (!canTrackEvents()) return;
    ensureDataLayer().push({ event: eventName, ...eventData });
  } catch {
    // fail-safe: adblockers ou ambientes sem dataLayer não devem quebrar a UI
  }
}

/** @deprecated Prefer {@link trackEvent} */
export function pushToDataLayer(event: string, payload?: Record<string, unknown>): void {
  trackEvent(event, payload);
}

/** SHA-256 hex (lowercase) para Advanced Matching via GTM. */
export async function sha256Hex(value: string): Promise<string> {
  const data = new TextEncoder().encode(value);
  const digest = await crypto.subtle.digest("SHA-256", data);
  return Array.from(new Uint8Array(digest))
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");
}

/** Normaliza e hasheia e-mail (trim + lowercase). */
export async function hashEmail(email: string): Promise<string> {
  const normalized = email.trim().toLowerCase();
  if (!normalized) return "";
  return sha256Hex(normalized);
}

/**
 * Normaliza telefone BR (só dígitos; prefixa 55 se 10–11 dígitos) e hasheia.
 */
export async function hashPhone(phone: string): Promise<string> {
  let digits = phone.replace(/\D/g, "");
  if (!digits) return "";
  if (digits.length === 10 || digits.length === 11) {
    digits = `55${digits}`;
  }
  return sha256Hex(digits);
}

/** Google Consent Mode v2 — default denied antes de qualquer tag. */
export function initConsentDefaults(): void {
  if (consentDefaultsInitialized || typeof window === "undefined") return;
  consentDefaultsInitialized = true;

  try {
    ensureDataLayer().push({
      event: "consent_default",
      analytics_storage: "denied",
      ad_storage: "denied",
      ad_user_data: "denied",
      ad_personalization: "denied",
    });
  } catch {
    // ignore
  }
}

function pushConsentUpdate(granted: boolean): void {
  try {
    ensureDataLayer().push({
      event: granted ? "consent_granted" : "consent_denied",
      analytics_storage: granted ? "granted" : "denied",
      ad_storage: granted ? "granted" : "denied",
      ad_user_data: granted ? "granted" : "denied",
      ad_personalization: granted ? "granted" : "denied",
    });
  } catch {
    // ignore
  }
}

export function loadGtm(containerId: string): void {
  if (!containerId || typeof document === "undefined") return;
  if (document.getElementById(GTM_SCRIPT_ID)) return;

  ensureDataLayer().push({ "gtm.start": Date.now(), event: "gtm.js" });

  const script = document.createElement("script");
  script.id = GTM_SCRIPT_ID;
  script.async = true;
  script.src = `https://www.googletagmanager.com/gtm.js?id=${encodeURIComponent(containerId)}`;
  document.head.appendChild(script);

  if (!document.getElementById(GTM_NOSCRIPT_ID)) {
    const noscript = document.createElement("noscript");
    noscript.id = GTM_NOSCRIPT_ID;
    noscript.innerHTML = `<iframe src="https://www.googletagmanager.com/ns.html?id=${encodeURIComponent(containerId)}" height="0" width="0" style="display:none;visibility:hidden"></iframe>`;
    document.body.prepend(noscript);
  }
}

/** Carrega apenas o GTM; Pixel e GA4 devem ser tags dentro do container. */
export function enableMarketingTracking(): void {
  pushConsentUpdate(true);

  const gtmId = getGtmContainerId();
  if (gtmId) {
    loadGtm(gtmId);
  }
}

export function disableMarketingTracking(): void {
  pushConsentUpdate(false);
}

/** @deprecated Use disableMarketingTracking */
export function revokeGtmConsent(): void {
  disableMarketingTracking();
}

export function getGtmContainerId(): string | undefined {
  const id = import.meta.env.VITE_GTM_ID?.trim();
  return id || undefined;
}

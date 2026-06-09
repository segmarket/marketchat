import {
  hasAnalyticsConsent,
  hasMarketingConsent,
} from "../features/marketing/cookieConsent";
import { isAppHost } from "./host";

declare global {
  interface Window {
    dataLayer?: Record<string, unknown>[];
    fbq?: (...args: unknown[]) => void;
    _fbq?: (...args: unknown[]) => void;
  }
}

const GTM_SCRIPT_ID = "marketchat-gtm-script";
const GTM_NOSCRIPT_ID = "marketchat-gtm-noscript";
const META_PIXEL_SCRIPT_ID = "marketchat-meta-pixel-script";

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
 * Dispara evento customizado no dataLayer (GTM/GA4).
 * Não envie PII (e-mail, CPF, telefone, senha) em eventData.
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

export function loadMetaPixel(pixelId: string): void {
  if (!pixelId || typeof document === "undefined") return;
  if (document.getElementById(META_PIXEL_SCRIPT_ID)) return;

  const fbq = function (...args: unknown[]) {
    if (fbq.callMethod) {
      fbq.callMethod(...args);
    } else {
      fbq.queue.push(args);
    }
  } as typeof window.fbq & {
    callMethod?: (...args: unknown[]) => void;
    queue: unknown[][];
    loaded?: boolean;
    version?: string;
    push?: (...args: unknown[]) => void;
  };

  if (!window._fbq) window._fbq = fbq;
  window.fbq = fbq;
  fbq.push = fbq;
  fbq.loaded = true;
  fbq.version = "2.0";
  fbq.queue = [];

  const script = document.createElement("script");
  script.id = META_PIXEL_SCRIPT_ID;
  script.async = true;
  script.src = "https://connect.facebook.net/en_US/fbevents.js";
  document.head.appendChild(script);

  window.fbq?.("init", pixelId);
  window.fbq?.("track", "PageView");
}

export function enableMarketingTracking(): void {
  pushConsentUpdate(true);

  const gtmId = getGtmContainerId();
  if (gtmId) {
    loadGtm(gtmId);
  }

  const pixelId = getMetaPixelId();
  if (pixelId) {
    loadMetaPixel(pixelId);
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

export function getMetaPixelId(): string | undefined {
  const id = import.meta.env.VITE_META_PIXEL_ID?.trim();
  return id || undefined;
}

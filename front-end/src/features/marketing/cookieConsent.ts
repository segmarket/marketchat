export const COOKIE_CONSENT_STORAGE_KEY = "marketchat_cookie_consent";
export const CONSENT_CHANGE_EVENT = "marketchat:consent-change";

const CONSENT_COOKIE_MAX_AGE_SECONDS = 60 * 60 * 24 * 365;

export type CookieConsentPreferences = {
  analytics: boolean;
  marketing: boolean;
};

/** @deprecated Use CookieConsentPreferences */
export type CookieConsentStatus = "accepted" | "rejected";

function isPreferences(value: unknown): value is CookieConsentPreferences {
  if (!value || typeof value !== "object") return false;
  const obj = value as Record<string, unknown>;
  return typeof obj.analytics === "boolean" && typeof obj.marketing === "boolean";
}

function migrateLegacyValue(raw: string): CookieConsentPreferences | null {
  if (raw === "accepted") {
    return { analytics: true, marketing: true };
  }
  if (raw === "rejected") {
    return { analytics: false, marketing: false };
  }
  return null;
}

function parsePreferencesRaw(raw: string): CookieConsentPreferences | null {
  const legacy = migrateLegacyValue(raw);
  if (legacy) return legacy;

  try {
    const parsed = JSON.parse(raw) as unknown;
    if (isPreferences(parsed)) return parsed;
  } catch {
    // ignore invalid JSON
  }
  return null;
}

function useSharedConsentCookie(): boolean {
  if (typeof window === "undefined") return false;
  const host = window.location.hostname.toLowerCase();
  return host === "marketchat.com.br" || host.endsWith(".marketchat.com.br");
}

function readConsentCookie(): CookieConsentPreferences | null {
  if (typeof document === "undefined" || !useSharedConsentCookie()) return null;

  const prefix = `${COOKIE_CONSENT_STORAGE_KEY}=`;
  const match = document.cookie.split("; ").find((row) => row.startsWith(prefix));
  if (!match) return null;

  const raw = decodeURIComponent(match.slice(prefix.length));
  return parsePreferencesRaw(raw);
}

function writeConsentCookie(prefs: CookieConsentPreferences): void {
  if (typeof document === "undefined" || !useSharedConsentCookie()) return;

  const value = encodeURIComponent(JSON.stringify(prefs));
  const secure = window.location.protocol === "https:" ? "; Secure" : "";
  document.cookie = `${COOKIE_CONSENT_STORAGE_KEY}=${value}; path=/; max-age=${CONSENT_COOKIE_MAX_AGE_SECONDS}; domain=.marketchat.com.br; SameSite=Lax${secure}`;
}

export function getConsentPreferences(): CookieConsentPreferences | null {
  try {
    const fromCookie = readConsentCookie();
    if (fromCookie) {
      localStorage.setItem(COOKIE_CONSENT_STORAGE_KEY, JSON.stringify(fromCookie));
      return fromCookie;
    }

    const raw = localStorage.getItem(COOKIE_CONSENT_STORAGE_KEY);
    if (!raw) return null;

    const prefs = parsePreferencesRaw(raw);
    if (prefs) {
      writeConsentCookie(prefs);
      return prefs;
    }
    return null;
  } catch {
    return null;
  }
}

/** @deprecated Use getConsentPreferences */
export function getCookieConsent(): CookieConsentStatus | null {
  const prefs = getConsentPreferences();
  if (!prefs) return null;
  if (prefs.analytics && prefs.marketing) return "accepted";
  return "rejected";
}

export function saveConsentPreferences(prefs: CookieConsentPreferences): void {
  try {
    localStorage.setItem(COOKIE_CONSENT_STORAGE_KEY, JSON.stringify(prefs));
    writeConsentCookie(prefs);
  } catch {
    // ignore
  }
}

/** @deprecated Use saveConsentPreferences */
export function setCookieConsent(status: CookieConsentStatus): void {
  saveConsentPreferences(
    status === "accepted"
      ? { analytics: true, marketing: true }
      : { analytics: false, marketing: false },
  );
}

export function isConsentPending(): boolean {
  return getConsentPreferences() === null;
}

export function hasMarketingConsent(): boolean {
  return getConsentPreferences()?.marketing === true;
}

export function hasAnalyticsConsent(): boolean {
  return getConsentPreferences()?.analytics === true;
}

export function dispatchConsentChange(prefs: CookieConsentPreferences): void {
  if (typeof window === "undefined") return;
  window.dispatchEvent(
    new CustomEvent(CONSENT_CHANGE_EVENT, { detail: prefs }),
  );
}

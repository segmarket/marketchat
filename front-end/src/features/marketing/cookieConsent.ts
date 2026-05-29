export const COOKIE_CONSENT_STORAGE_KEY = "marketchat_cookie_consent";

export type CookieConsentStatus = "accepted" | "rejected";

export function getCookieConsent(): CookieConsentStatus | null {
  try {
    const value = localStorage.getItem(COOKIE_CONSENT_STORAGE_KEY);
    if (value === "accepted" || value === "rejected") {
      return value;
    }
    return null;
  } catch {
    return null;
  }
}

export function setCookieConsent(status: CookieConsentStatus): void {
  try {
    localStorage.setItem(COOKIE_CONSENT_STORAGE_KEY, status);
  } catch {
    // ignore
  }
}

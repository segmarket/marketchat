import { useEffect, useMemo, useRef } from "react";
import {
  appendAttributionToUrl,
  loadAttribution,
  parseAttributionFromSearch,
  saveAttribution,
} from "../features/attribution/storage";
import {
  CONSENT_CHANGE_EVENT,
  hasMarketingConsent,
  type CookieConsentPreferences,
} from "../features/marketing/cookieConsent";
import type { AttributionParams } from "../features/attribution/types";
import { getAppUrl } from "../utils/host";

export function useUTM() {
  const pendingFromUrl = useRef<AttributionParams | null>(null);

  useEffect(() => {
    const fromUrl = parseAttributionFromSearch(window.location.search);
    pendingFromUrl.current = fromUrl;

    if (hasMarketingConsent()) {
      saveAttribution(fromUrl);
    }

    function onConsentChange(event: Event) {
      const prefs = (event as CustomEvent<CookieConsentPreferences>).detail;
      if (prefs?.marketing && pendingFromUrl.current) {
        saveAttribution(pendingFromUrl.current);
      }
    }

    window.addEventListener(CONSENT_CHANGE_EVENT, onConsentChange);
    return () => window.removeEventListener(CONSENT_CHANGE_EVENT, onConsentChange);
  }, []);

  const attribution = useMemo(() => loadAttribution(), []);

  function buildSignupUrl(path = "/auth/signup"): string {
    return appendAttributionToUrl(getAppUrl(path), loadAttribution());
  }

  return { attribution, buildSignupUrl };
}

export type { AttributionParams };

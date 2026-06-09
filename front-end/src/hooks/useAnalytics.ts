import { useEffect } from "react";
import {
  CONSENT_CHANGE_EVENT,
  hasAnalyticsConsent,
  hasMarketingConsent,
  type CookieConsentPreferences,
} from "../features/marketing/cookieConsent";
import { isAppHost } from "../utils/host";
import { enableMarketingTracking, disableMarketingTracking } from "../utils/analytics";

function shouldEnableTracking(): boolean {
  if (hasMarketingConsent()) return true;
  return isAppHost() && hasAnalyticsConsent();
}

/** Ativa GTM/Meta Pixel somente após consentimento LGPD. */
export function useAnalytics(): void {
  useEffect(() => {
    if (shouldEnableTracking()) {
      enableMarketingTracking();
    }

    function onConsentChange(event: Event) {
      const prefs = (event as CustomEvent<CookieConsentPreferences>).detail;
      const granted = prefs?.marketing || (isAppHost() && prefs?.analytics);
      if (granted) {
        enableMarketingTracking();
      } else {
        disableMarketingTracking();
      }
    }

    window.addEventListener(CONSENT_CHANGE_EVENT, onConsentChange);
    return () => window.removeEventListener(CONSENT_CHANGE_EVENT, onConsentChange);
  }, []);
}

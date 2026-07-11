import { useEffect, useRef } from "react";
import { useLocation } from "react-router";
import {
  CONSENT_CHANGE_EVENT,
  hasAnalyticsConsent,
  hasMarketingConsent,
  type CookieConsentPreferences,
} from "../features/marketing/cookieConsent";
import { enableMarketingTracking, disableMarketingTracking } from "../utils/analytics";
import { isAppHost } from "../utils/host";
import {
  isMetaPixelInitialized,
  isPublicPagePath,
  trackMetaPageView,
} from "../utils/metaPixel";

function shouldEnableTracking(): boolean {
  if (hasMarketingConsent()) return true;
  return isAppHost() && hasAnalyticsConsent();
}

/** Ativa Meta Pixel + GTM somente após consentimento LGPD. */
export function useAnalytics(): void {
  const { pathname } = useLocation();
  const isFirstPathEffect = useRef(true);

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

  useEffect(() => {
    if (!shouldEnableTracking() || !isMetaPixelInitialized()) return;
    if (!isPublicPagePath(pathname, isAppHost())) return;

    if (isFirstPathEffect.current) {
      isFirstPathEffect.current = false;
      return;
    }

    trackMetaPageView();
  }, [pathname]);
}

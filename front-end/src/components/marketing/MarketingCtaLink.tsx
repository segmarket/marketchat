import { useState, type MouseEvent, type ReactNode } from "react";
import {
  appendAttributionToUrl,
  loadAttribution,
} from "../../features/attribution/storage";
import { ATTRIBUTION_PARAM_KEYS } from "../../features/attribution/types";
import {
  ANALYTICS_EVENTS,
  type CtaLocation,
} from "../../constants/analyticsEvents";
import { trackEvent } from "../../utils/analytics";
import { getAppUrl } from "../../utils/host";

type MarketingCtaLinkProps = {
  children: ReactNode;
  className?: string;
  path?: string;
  trackEvent?: boolean;
  analyticsLocation?: CtaLocation;
};

function attributionPayload(): Record<string, string> {
  const attribution = loadAttribution();
  const payload: Record<string, string> = {};
  for (const key of ATTRIBUTION_PARAM_KEYS) {
    const value = attribution[key];
    if (value) payload[key] = value;
  }
  return payload;
}

export default function MarketingCtaLink({
  children,
  className = "",
  path = "/auth/signup",
  trackEvent: shouldTrack = true,
  analyticsLocation,
}: MarketingCtaLinkProps) {
  const [isNavigating, setIsNavigating] = useState(false);
  const href = appendAttributionToUrl(getAppUrl(path));

  function handleClick(event: MouseEvent<HTMLAnchorElement>) {
    if (shouldTrack) {
      trackEvent(ANALYTICS_EVENTS.CLICK_CTA_TRIAL, {
        ...(analyticsLocation ? { location: analyticsLocation } : {}),
        ...attributionPayload(),
      });
    }
    if (!event.metaKey && !event.ctrlKey && !event.shiftKey && event.button === 0) {
      setIsNavigating(true);
    }
  }

  return (
    <a
      href={href}
      className={className}
      onClick={handleClick}
      aria-busy={isNavigating}
    >
      {isNavigating ? "Redirecionando…" : children}
    </a>
  );
}

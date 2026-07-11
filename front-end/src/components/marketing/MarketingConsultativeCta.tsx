import type { ReactNode } from "react";
import {
  loadAttribution,
} from "../../features/attribution/storage";
import { ATTRIBUTION_PARAM_KEYS } from "../../features/attribution/types";
import {
  ANALYTICS_EVENTS,
  type CtaLocation,
} from "../../constants/analyticsEvents";
import { CONSULTATIVE_FORM_CTA } from "../../constants/marketingCopy";
import { useConsultativeLead } from "../../features/consultative/ConsultativeLeadContext";
import { trackEvent } from "../../utils/analytics";

type MarketingConsultativeCtaProps = {
  children?: ReactNode;
  className?: string;
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

export default function MarketingConsultativeCta({
  children = CONSULTATIVE_FORM_CTA,
  className = "",
  analyticsLocation,
}: MarketingConsultativeCtaProps) {
  const { openLeadForm } = useConsultativeLead();

  function handleClick() {
    trackEvent(ANALYTICS_EVENTS.CLICK_CTA_TRIAL, {
      ...(analyticsLocation ? { location: analyticsLocation } : {}),
      ...attributionPayload(),
    });
    openLeadForm();
  }

  return (
    <button type="button" className={className} onClick={handleClick}>
      {children}
    </button>
  );
}

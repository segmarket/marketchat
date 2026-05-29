import { useEffect } from "react";
import { getCookieConsent } from "../../features/marketing/cookieConsent";
import { getGtmContainerId, loadGtm, pushToDataLayer } from "../../utils/analytics";

/** Inicializa GTM quando o usuário já aceitou cookies em visita anterior. */
export default function MarketingAnalytics() {
  useEffect(() => {
    const consent = getCookieConsent();
    if (consent === "accepted") {
      const gtmId = getGtmContainerId();
      if (gtmId) {
        loadGtm(gtmId);
      }
      pushToDataLayer("consent_granted");
    }
  }, []);

  return null;
}

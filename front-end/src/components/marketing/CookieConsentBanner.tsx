import { useEffect, useState } from "react";
import { Link } from "react-router";
import {
  COOKIE_CONSENT_STORAGE_KEY,
  getCookieConsent,
  setCookieConsent,
  type CookieConsentStatus,
} from "../../features/marketing/cookieConsent";
import { getGtmContainerId, loadGtm, pushToDataLayer, revokeGtmConsent } from "../../utils/analytics";

type Props = {
  onConsentChange?: (status: CookieConsentStatus) => void;
};

export default function CookieConsentBanner({ onConsentChange }: Props) {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    setVisible(getCookieConsent() === null);
  }, []);

  function applyConsent(status: CookieConsentStatus) {
    setCookieConsent(status);
    setVisible(false);
    onConsentChange?.(status);

    if (status === "accepted") {
      const gtmId = getGtmContainerId();
      if (gtmId) {
        loadGtm(gtmId);
      }
      pushToDataLayer("consent_granted");
    } else {
      revokeGtmConsent();
    }
  }

  if (!visible) {
    return null;
  }

  return (
    <div
      className="fixed inset-x-0 bottom-0 z-[60] border-t border-brand-500/30 bg-gray-950/95 p-4 shadow-2xl backdrop-blur-md sm:p-5"
      role="dialog"
      aria-label="Consentimento de cookies"
    >
      <div className="mx-auto flex max-w-7xl flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <p className="text-sm leading-relaxed text-gray-300">
          Utilizamos cookies para otimizar sua experiência e analisar nosso tráfego. Ao continuar
          navegando, você concorda com nossa{" "}
          <Link to="/privacidade" className="font-medium text-brand-400 underline hover:text-brand-300">
            Política de Privacidade
          </Link>
          .
        </p>
        <div className="flex shrink-0 gap-3">
          <button
            type="button"
            onClick={() => applyConsent("rejected")}
            className="rounded-md border border-gray-600 px-4 py-2 text-sm font-medium text-gray-300 transition-colors hover:border-gray-500 hover:text-white"
          >
            Recusar
          </button>
          <button
            type="button"
            onClick={() => applyConsent("accepted")}
            className="rounded-md bg-green-500 px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-green-600"
          >
            Aceitar
          </button>
        </div>
      </div>
    </div>
  );
}

export { COOKIE_CONSENT_STORAGE_KEY };

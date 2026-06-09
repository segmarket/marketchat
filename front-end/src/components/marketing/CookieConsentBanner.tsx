import { useEffect, useRef, useState } from "react";
import { Link } from "react-router";
import {
  COOKIE_CONSENT_STORAGE_KEY,
  dispatchConsentChange,
  getConsentPreferences,
  isConsentPending,
  saveConsentPreferences,
  type CookieConsentPreferences,
} from "../../features/marketing/cookieConsent";

type Props = {
  onConsentChange?: (prefs: CookieConsentPreferences) => void;
  onHeightChange?: (height: number) => void;
};

const COOKIE_BUTTON_CLASS =
  "min-h-[44px] rounded-md border border-gray-500 px-4 py-2 text-sm font-medium text-gray-200 transition-colors hover:border-gray-400 hover:text-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white focus-visible:ring-offset-2 focus-visible:ring-offset-gray-950";

const ACCEPT_ALL: CookieConsentPreferences = { analytics: true, marketing: true };
const ESSENTIALS_ONLY: CookieConsentPreferences = { analytics: false, marketing: false };

export default function CookieConsentBanner({ onConsentChange, onHeightChange }: Props) {
  const [visible, setVisible] = useState(false);
  const bannerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setVisible(isConsentPending());
  }, []);

  useEffect(() => {
    if (!visible) {
      onHeightChange?.(0);
      document.documentElement.style.removeProperty("--cookie-banner-height");
      return;
    }

    function updateHeight() {
      const height = bannerRef.current?.offsetHeight ?? 0;
      onHeightChange?.(height);
      document.documentElement.style.setProperty("--cookie-banner-height", `${height}px`);
    }

    updateHeight();
    const observer = new ResizeObserver(updateHeight);
    if (bannerRef.current) observer.observe(bannerRef.current);
    window.addEventListener("resize", updateHeight);
    return () => {
      observer.disconnect();
      window.removeEventListener("resize", updateHeight);
    };
  }, [visible, onHeightChange]);

  function applyConsent(prefs: CookieConsentPreferences) {
    saveConsentPreferences(prefs);
    setVisible(false);
    onConsentChange?.(prefs);
    onHeightChange?.(0);
    document.documentElement.style.removeProperty("--cookie-banner-height");
    dispatchConsentChange(prefs);
  }

  if (!visible) {
    return null;
  }

  return (
    <div
      ref={bannerRef}
      className="fixed inset-x-0 bottom-0 z-[60] border-t border-gray-700 bg-gray-950/95 p-3 shadow-lg backdrop-blur-md sm:p-4"
      role="dialog"
      aria-label="Consentimento de cookies"
    >
      <div className="mx-auto flex max-w-7xl flex-col gap-3 sm:flex-row sm:items-center sm:justify-between sm:gap-4">
        <p className="text-sm leading-relaxed text-gray-300">
          Utilizamos cookies para melhorar sua experiência, analisar o tráfego e medir campanhas.
          Veja nossa{" "}
          <Link
            to="/privacidade"
            className="font-medium text-brand-400 underline hover:text-brand-300 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-400 rounded-sm"
          >
            Política de Privacidade
          </Link>
          .
        </p>
        <div className="flex shrink-0 gap-3">
          <button
            type="button"
            onClick={() => applyConsent(ESSENTIALS_ONLY)}
            className={COOKIE_BUTTON_CLASS}
          >
            Apenas essenciais
          </button>
          <button
            type="button"
            onClick={() => applyConsent(ACCEPT_ALL)}
            className={COOKIE_BUTTON_CLASS}
          >
            Aceitar todos
          </button>
        </div>
      </div>
    </div>
  );
}

export { COOKIE_CONSENT_STORAGE_KEY };

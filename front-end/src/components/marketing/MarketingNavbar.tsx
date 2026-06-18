import { useEffect, useState } from "react";
import { Menu, X } from "lucide-react";
import { getAppUrl } from "../../utils/host";
import { CTA_LOCATIONS } from "../../constants/analyticsEvents";
import {
  CTA_LOGIN_LINK_CLASS,
  CTA_PRIMARY_CLASS,
  CTA_TRIAL_PRIMARY,
  NAV_ANCHORS,
} from "../../constants/marketingCopy";
import MarketingBrandLogo, { MARKETING_LOGO_CLASS } from "./MarketingBrandLogo";
import MarketingCtaLink from "./MarketingCtaLink";

export default function MarketingNavbar() {
  const [menuOpen, setMenuOpen] = useState(false);

  useEffect(() => {
    if (!menuOpen) return;
    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") setMenuOpen(false);
    }
    document.body.style.overflow = "hidden";
    window.addEventListener("keydown", onKeyDown);
    return () => {
      document.body.style.overflow = "";
      window.removeEventListener("keydown", onKeyDown);
    };
  }, [menuOpen]);

  function closeMenu() {
    setMenuOpen(false);
  }

  return (
    <header className="sticky top-0 z-50 border-b border-gray-200 bg-white/80 backdrop-blur-md">
      <div className="mx-auto flex max-w-7xl items-center justify-between gap-4 px-4 py-4 sm:px-6 lg:px-8">
        <a href="/" className="flex items-center">
          <MarketingBrandLogo showWordmark={false} imageClassName={MARKETING_LOGO_CLASS} />
        </a>

        <nav className="hidden items-center gap-8 md:flex" aria-label="Principal">
          {NAV_ANCHORS.map((link) => (
            <a
              key={link.href}
              href={link.href}
              className="rounded-sm text-sm font-medium text-gray-600 transition-colors hover:text-brand-600 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500 focus-visible:ring-offset-2"
            >
              {link.label}
            </a>
          ))}
        </nav>

        <div className="flex items-center gap-2 sm:gap-3">
          <MarketingCtaLink
            path="/auth/signup"
            className={`${CTA_PRIMARY_CLASS} px-4 py-2.5 text-sm sm:px-6 sm:py-3`}
            analyticsLocation={CTA_LOCATIONS.NAVBAR}
          >
            {CTA_TRIAL_PRIMARY}
          </MarketingCtaLink>
          <a href={getAppUrl()} className={`hidden md:inline-flex ${CTA_LOGIN_LINK_CLASS}`}>
            Acessar sistema
          </a>
          <button
            type="button"
            className="inline-flex min-h-[44px] min-w-[44px] items-center justify-center rounded-md border border-gray-200 text-gray-700 md:hidden focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500"
            aria-label={menuOpen ? "Fechar menu" : "Abrir menu"}
            aria-expanded={menuOpen}
            onClick={() => setMenuOpen((open) => !open)}
          >
            {menuOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
          </button>
        </div>
      </div>

      {menuOpen ? (
        <div className="border-t border-gray-200 bg-white md:hidden">
          <nav className="mx-auto flex max-w-7xl flex-col px-4 py-4" aria-label="Menu mobile">
            {NAV_ANCHORS.map((link) => (
              <a
                key={link.href}
                href={link.href}
                onClick={closeMenu}
                className="flex min-h-[48px] items-center text-base font-medium text-gray-800 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-brand-500"
              >
                {link.label}
              </a>
            ))}
            <a
              href={getAppUrl()}
              onClick={closeMenu}
              className="flex min-h-[48px] items-center text-base font-medium text-gray-600 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-brand-500"
            >
              Acessar sistema
            </a>
          </nav>
        </div>
      ) : null}
    </header>
  );
}

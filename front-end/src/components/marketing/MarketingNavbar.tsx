import { getAppUrl } from "../../utils/host";
import MarketingBrandLogo, { MARKETING_LOGO_CLASS } from "./MarketingBrandLogo";
import MarketingCtaLink from "./MarketingCtaLink";

const NAV_LINKS = [
  { label: "Pilares", href: "#pilares" },
  { label: "Para o dono", href: "#para-o-dono" },
  { label: "Preços", href: "#precos" },
] as const;

export default function MarketingNavbar() {
  return (
    <header className="sticky top-0 z-50 border-b border-gray-200 bg-white/80 backdrop-blur-md">
      <div className="mx-auto flex max-w-7xl items-center justify-between gap-4 px-4 py-4 sm:px-6 lg:px-8">
        <a href="/" className="flex items-center">
          <MarketingBrandLogo showWordmark={false} imageClassName={MARKETING_LOGO_CLASS} />
        </a>

        <nav className="hidden items-center gap-8 md:flex">
          {NAV_LINKS.map((link) => (
            <a
              key={link.href}
              href={link.href}
              className="text-sm font-medium text-gray-600 transition-colors hover:text-brand-600"
            >
              {link.label}
            </a>
          ))}
        </nav>

        <div className="flex items-center gap-2 sm:gap-3">
          <MarketingCtaLink
            path="/auth/signup"
            className="hidden rounded-md bg-green-500 px-3 py-2 text-sm font-semibold text-white transition-colors hover:bg-green-600 sm:inline-flex"
          >
            Teste grátis
          </MarketingCtaLink>
          <a
            href={getAppUrl()}
            className="rounded-md bg-brand-500 px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-brand-600"
          >
            Acessar Sistema
          </a>
        </div>
      </div>
    </header>
  );
}

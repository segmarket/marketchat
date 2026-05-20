import { getAppUrl } from "../../utils/host";

const NAV_LINKS = [
  { label: "Diferenciais", href: "#diferenciais" },
  { label: "Como Funciona", href: "#como-funciona" },
  { label: "Preços", href: "#precos" },
] as const;

export default function MarketingNavbar() {
  return (
    <header className="sticky top-0 z-50 border-b border-gray-200 bg-white/80 backdrop-blur-md">
      <div className="mx-auto flex max-w-7xl items-center justify-between gap-4 px-4 py-4 sm:px-6 lg:px-8">
        <a href="/" className="flex items-center gap-2">
          <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-brand-500 text-sm font-bold text-white">
            MC
          </span>
          <span className="text-lg font-semibold text-gray-900">MarketChat</span>
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

        <a
          href={getAppUrl()}
          className="rounded-md bg-brand-500 px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-brand-600"
        >
          Acessar Sistema
        </a>
      </div>
    </header>
  );
}

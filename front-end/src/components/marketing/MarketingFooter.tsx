import { appUrl } from "../../utils/host";

export default function MarketingFooter() {
  const year = new Date().getFullYear();

  return (
    <footer className="border-t border-gray-200 bg-white px-4 py-12 sm:px-6 lg:px-8">
      <div className="mx-auto flex max-w-7xl flex-col items-center justify-between gap-6 sm:flex-row">
        <div className="flex items-center gap-2">
          <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-brand-500 text-xs font-bold text-white">
            MC
          </span>
          <span className="font-semibold text-gray-900">MarketChat</span>
        </div>
        <p className="text-sm text-gray-500">
          © {year} MarketChat. Mercados autônomos inteligentes via WhatsApp.
        </p>
        <a
          href={appUrl("/login")}
          className="text-sm font-medium text-brand-600 hover:text-brand-700"
        >
          Acessar o sistema
        </a>
      </div>
    </footer>
  );
}

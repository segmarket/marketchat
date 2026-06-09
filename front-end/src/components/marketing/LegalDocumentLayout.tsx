import type { ReactNode } from "react";
import { Link } from "react-router";
import PageMeta from "../common/PageMeta";
import MarketingBrandLogo from "./MarketingBrandLogo";

type Props = {
  title: string;
  description: string;
  path: string;
  children: ReactNode;
};

export default function LegalDocumentLayout({ title, description, path, children }: Props) {
  return (
    <div className="min-h-screen bg-white font-outfit text-gray-900 antialiased">
      <PageMeta title={title} description={description} path={path} />
      <header className="border-b border-gray-200 bg-white">
        <div className="mx-auto flex max-w-3xl items-center justify-between px-4 py-4 sm:px-6">
          <Link to="/" className="inline-flex items-center gap-2">
            <MarketingBrandLogo showWordmark={false} />
          </Link>
          <Link
            to="/"
            className="rounded-sm text-sm font-medium text-brand-600 hover:text-brand-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500 focus-visible:ring-offset-2"
          >
            Voltar à landing
          </Link>
        </div>
      </header>

      <main className="mx-auto max-w-3xl px-4 py-12 sm:px-6">{children}</main>
    </div>
  );
}

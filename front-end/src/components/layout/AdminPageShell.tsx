import type { ReactNode } from "react";
import PageBreadcrumb from "../common/PageBreadCrumb";
import PageMeta from "../common/PageMeta";

/** Largura única do conteúdo admin (área entre sidebar e borda direita). */
export const adminPageRootClassName = "w-full min-w-0";

/** Card branco padrão do admin (mesmo visual do Painel de Vendas). */
export const adminPanelCardClassName =
  "w-full min-w-0 rounded-2xl border border-gray-200 bg-white p-5 dark:border-gray-800 dark:bg-white/[0.03] md:p-6";

type PanelCardProps = {
  children: ReactNode;
  className?: string;
  description?: string;
};

export function AdminPanelCard({ children, className = "", description }: PanelCardProps) {
  return (
    <div className={`${adminPanelCardClassName} ${className}`.trim()}>
      {description ? (
        <p className="mb-4 text-sm text-gray-500 dark:text-gray-400">{description}</p>
      ) : null}
      {children}
    </div>
  );
}

type PageLayoutProps = {
  pageTitle: string;
  metaTitle?: string;
  metaDescription?: string;
  description?: string;
  children: ReactNode;
};

/** Meta + breadcrumb + card padrão (largura alinhada ao Painel de Vendas). */
export default function AdminPageLayout({
  pageTitle,
  metaTitle,
  metaDescription,
  description,
  children,
}: PageLayoutProps) {
  return (
    <div className={adminPageRootClassName}>
      <PageMeta
        title={metaTitle ?? `${pageTitle} | MarketChat`}
        description={metaDescription ?? pageTitle}
      />
      <PageBreadcrumb pageTitle={pageTitle} />
      <AdminPanelCard description={description}>{children}</AdminPanelCard>
    </div>
  );
}

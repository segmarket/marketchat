import type { ReactNode } from "react";
import PageBreadcrumb from "../common/PageBreadCrumb";
import PageMeta from "../common/PageMeta";

/** Largura única do conteúdo admin (área entre sidebar e borda direita). */
export const adminPageRootClassName = "w-full min-w-0";

/** Card branco padrão do admin (mesmo visual do Painel de Vendas). */
export const adminPanelCardClassName =
  "w-full min-w-0 rounded-2xl border border-gray-200 bg-white p-4 dark:border-gray-800 dark:bg-white/[0.03] md:p-6";

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
  /** Classes extras no card principal (ex.: `!p-0` para layout mestre-detalhe). */
  panelClassName?: string;
  /** Classes extras no root (ex.: `h-full min-h-0 flex-1` em rotas fullscreen). */
  className?: string;
  /** Classes extras no breadcrumb (ex.: `mb-3` em layouts compactos). */
  breadcrumbClassName?: string;
  children: ReactNode;
};

/** Meta + breadcrumb + card padrão (largura alinhada ao Painel de Vendas). */
export default function AdminPageLayout({
  pageTitle,
  metaTitle,
  metaDescription,
  description,
  panelClassName = "",
  className = "",
  breadcrumbClassName = "",
  children,
}: PageLayoutProps) {
  const descriptionOutsideCard =
    Boolean(description) && (panelClassName.includes("!p-0") || panelClassName.includes(" p-0"));

  return (
    <div className={`${adminPageRootClassName} ${className}`.trim()}>
      <PageMeta
        title={metaTitle ?? `${pageTitle} | MarketChat`}
        description={metaDescription ?? pageTitle}
        noIndex
      />
      <PageBreadcrumb pageTitle={pageTitle} className={breadcrumbClassName} />
      {descriptionOutsideCard ? (
        <p className="mb-4 shrink-0 text-sm text-gray-500 dark:text-gray-400">{description}</p>
      ) : null}
      <AdminPanelCard
        description={descriptionOutsideCard ? undefined : description}
        className={panelClassName}
      >
        {children}
      </AdminPanelCard>
    </div>
  );
}

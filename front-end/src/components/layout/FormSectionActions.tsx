import type { ReactNode } from "react";

type FormSectionActionsProps = {
  children: ReactNode;
  className?: string;
};

/** Alinha ações (ex.: Salvar) na coluna direita do grid 1/3 + 2/3 */
export default function FormSectionActions({ children, className = "" }: FormSectionActionsProps) {
  return (
    <div className={`grid grid-cols-1 gap-6 lg:grid-cols-3 lg:gap-8 ${className}`}>
      <div className="hidden lg:block" aria-hidden />
      <div className="flex flex-wrap items-center justify-end gap-3 lg:col-span-2">{children}</div>
    </div>
  );
}

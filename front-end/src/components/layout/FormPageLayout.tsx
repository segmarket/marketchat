import type { ReactNode } from "react";

type FormPageLayoutProps = {
  children: ReactNode;
  /** Estende o fundo slate até as bordas do padding do AppLayout */
  fullBleed?: boolean;
};

/**
 * Shell de páginas com formulários: largura total, fundo slate e padding fluido.
 * Use em Configurações, cadastros e demais telas de formulário do admin.
 */
export default function FormPageLayout({ children, fullBleed = true }: FormPageLayoutProps) {
  return (
    <div
      className={
        fullBleed
          ? "-mx-4 mb-0 w-[calc(100%+2rem)] bg-slate-50 px-4 py-4 dark:bg-gray-950 md:-mx-6 md:w-[calc(100%+3rem)] md:px-6 md:py-6 xl:px-9"
          : "w-full bg-slate-50 px-4 py-4 dark:bg-gray-950 md:px-6 md:py-6 xl:px-9"
      }
    >
      <div className="mx-auto w-full max-w-none space-y-6">{children}</div>
    </div>
  );
}

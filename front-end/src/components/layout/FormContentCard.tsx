import type { ReactNode } from "react";

type FormContentCardProps = {
  children: ReactNode;
  className?: string;
};

/** Card branco para listagens e painéis dentro de FormPageLayout (Mercados, Produtos, etc.) */
export default function FormContentCard({ children, className = "" }: FormContentCardProps) {
  return (
    <div
      className={`rounded-lg border border-gray-200 bg-white p-5 shadow-theme-sm dark:border-gray-800 dark:bg-gray-900 md:p-6 ${className}`}
    >
      {children}
    </div>
  );
}

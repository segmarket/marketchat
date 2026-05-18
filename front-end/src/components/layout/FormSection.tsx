import type { ReactNode } from "react";

type FormSectionProps = {
  title: string;
  description: string;
  children: ReactNode;
  className?: string;
};

/**
 * Seção assimétrica: título/contexto (1/3) + card de formulário (2/3).
 */
export default function FormSection({ title, description, children, className = "" }: FormSectionProps) {
  return (
    <section className={`grid grid-cols-1 gap-6 lg:grid-cols-3 lg:gap-8 ${className}`}>
      <header className="lg:col-span-1">
        <h3 className="text-base font-semibold text-gray-900 dark:text-white/90">{title}</h3>
        <p className="mt-2 text-sm leading-relaxed text-gray-500 dark:text-gray-400">{description}</p>
      </header>
      <div className="lg:col-span-2">
        <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-theme-sm dark:border-gray-800 dark:bg-gray-900">
          {children}
        </div>
      </div>
    </section>
  );
}

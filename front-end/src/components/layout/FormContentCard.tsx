import type { ReactNode } from "react";
import { adminPanelCardClassName } from "./AdminPageShell";

type FormContentCardProps = {
  children: ReactNode;
  className?: string;
};

/** Card padrão do admin (mesmas bordas e largura do Painel de Vendas). */
export default function FormContentCard({ children, className = "" }: FormContentCardProps) {
  return (
    <div className={`${adminPanelCardClassName} ${className}`.trim()}>{children}</div>
  );
}

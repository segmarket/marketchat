import type { ReactNode } from "react";
import { adminPageRootClassName } from "./AdminPageShell";

type FormPageLayoutProps = {
  children: ReactNode;
};

/**
 * @deprecated Use AdminPageLayout. Mantido como pass-through de largura total.
 */
export default function FormPageLayout({ children }: FormPageLayoutProps) {
  return <div className={`${adminPageRootClassName} space-y-6`}>{children}</div>;
}

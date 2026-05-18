import type { LucideIcon } from "lucide-react";
import type { ReactNode } from "react";
import { Handle, Position } from "@xyflow/react";

const inputClass =
  "w-full rounded-lg border border-gray-300 px-2 py-1.5 text-xs focus:border-brand-300 focus:outline-none focus:ring-2 focus:ring-brand-500/30 dark:border-gray-700 dark:bg-gray-800 dark:text-gray-200";

type Props = {
  title: string;
  icon: LucideIcon;
  borderClass: string;
  headerClass: string;
  iconClass?: string;
  children: ReactNode;
  showTarget?: boolean;
  showSource?: boolean;
  readOnly?: boolean;
};

export function NodeShell({
  title,
  icon: Icon,
  borderClass,
  headerClass,
  iconClass = "text-white",
  children,
  showTarget = true,
  showSource = true,
  readOnly = false,
}: Props) {
  return (
    <div
      className={`min-w-[240px] max-w-[280px] rounded-xl border-2 bg-white p-0 shadow-theme-sm dark:bg-gray-900 ${borderClass} ${
        readOnly ? "opacity-90" : ""
      }`}
    >
      {showTarget && (
        <Handle
          type="target"
          position={Position.Top}
          className="!h-3 !w-3 !border-2 !border-white !bg-gray-400"
        />
      )}
      <div className={`flex items-center gap-2 rounded-t-[10px] px-4 py-2.5 ${headerClass}`}>
        <Icon className={`h-4 w-4 shrink-0 ${iconClass}`} />
        <span className="text-xs font-semibold uppercase tracking-wide text-white">{title}</span>
      </div>
      <div className="space-y-2 p-4 text-sm text-gray-700 dark:text-gray-300">{children}</div>
      {showSource && (
        <Handle
          type="source"
          position={Position.Bottom}
          className="!h-3 !w-3 !border-2 !border-white !bg-gray-400"
        />
      )}
    </div>
  );
}

export { inputClass };

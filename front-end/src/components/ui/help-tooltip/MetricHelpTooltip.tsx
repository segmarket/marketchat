import { Info } from "lucide-react";

type Props = {
  label: string;
  helpText: string;
  className?: string;
};

export default function MetricHelpTooltip({ label, helpText, className = "" }: Props) {
  return (
    <span
      className={`group relative inline-flex items-center gap-1.5 ${className}`}
    >
      <span className="text-sm text-gray-500 dark:text-gray-400">{label}</span>
      <span
        className="inline-flex shrink-0 rounded-full focus-within:outline-none focus-within:ring-2 focus-within:ring-brand-500/40"
        tabIndex={0}
        role="img"
        aria-label={helpText}
      >
        <Info className="h-4 w-4 text-gray-500 dark:text-gray-400" aria-hidden />
      </span>
      <span
        className="pointer-events-none absolute bottom-full left-0 z-20 mb-2 hidden w-48 rounded-md bg-gray-900 px-2 py-1.5 text-xs leading-snug text-white shadow-lg group-hover:block group-focus-within:block dark:bg-gray-950"
        role="tooltip"
      >
        {helpText}
      </span>
    </span>
  );
}

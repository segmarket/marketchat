import { X } from "lucide-react";

type Props = {
  onClick: () => void;
  label?: string;
};

export default function SupportTicketCloseButton({ onClick, label = "Fechar" }: Props) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-label={label}
      className="inline-flex shrink-0 items-center gap-1.5 rounded-lg border border-gray-200 px-3 py-1.5 text-xs font-medium text-gray-600 hover:bg-gray-50 dark:border-gray-700 dark:text-gray-300 dark:hover:bg-white/5"
    >
      <X className="size-4" />
      {label}
    </button>
  );
}

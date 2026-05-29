import { ArrowLeft, Sparkles, X } from "lucide-react";

type Props = {
  mode: "chat" | "ticket" | "ticket_sent";
  onClose: () => void;
  onBack?: () => void;
};

export default function SupportCopilotHeader({ mode, onClose, onBack }: Props) {
  return (
    <header className="relative z-10 flex shrink-0 items-center justify-between gap-3 border-b border-gray-200 bg-white p-4 dark:border-gray-800 dark:bg-gray-900">
      <div className="flex min-w-0 flex-1 items-center gap-2">
        {mode === "ticket" && onBack ? (
          <button
            type="button"
            aria-label="Voltar ao chat"
            onClick={onBack}
            className="shrink-0 rounded-lg p-1.5 text-gray-500 hover:bg-gray-100 dark:hover:bg-white/10"
          >
            <ArrowLeft className="size-5" />
          </button>
        ) : null}
        <div className="flex items-center gap-2">
          <Sparkles
            className="size-5 shrink-0 text-brand-500 dark:text-brand-400"
            strokeWidth={2}
            aria-hidden
          />
          <h2 className="text-base font-semibold leading-none text-gray-900 dark:text-white/90">
            Suporte Copilot
          </h2>
        </div>
      </div>
      <button
        type="button"
        onClick={onClose}
        aria-label="Fechar Suporte Copilot"
        className="inline-flex shrink-0 items-center gap-1.5 rounded-lg border border-gray-200 bg-gray-50 px-3 py-1.5 text-xs font-medium text-gray-700 hover:bg-gray-100 dark:border-gray-700 dark:bg-gray-800 dark:text-gray-200 dark:hover:bg-gray-700"
      >
        <X className="size-4" strokeWidth={2} />
        Fechar
      </button>
    </header>
  );
}

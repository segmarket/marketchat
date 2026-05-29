import { ArrowLeft } from "lucide-react";
import SupportTicketCloseButton from "./SupportTicketCloseButton";

type Props = {
  title?: string;
  onBack: () => void;
  onClose: () => void;
  trailing?: React.ReactNode;
};

/** Barra superior com voltar — visível mesmo durante carregamento do detalhe. */
export default function SupportTicketDetailToolbar({ title, onBack, onClose, trailing }: Props) {
  return (
    <header className="flex shrink-0 items-center justify-between gap-3 border-b border-gray-200 p-4 dark:border-gray-800">
      <div className="flex min-w-0 flex-1 items-center gap-2">
        <button
          type="button"
          onClick={onBack}
          aria-label="Voltar para a lista"
          className="shrink-0 rounded-lg p-1.5 text-gray-600 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-white/10"
        >
          <ArrowLeft className="size-5" />
        </button>
        {title ? (
          <h2 className="truncate text-base font-semibold text-gray-900 dark:text-white/90">
            {title}
          </h2>
        ) : (
          <span className="text-sm text-gray-500 dark:text-gray-400">Carregando chamado…</span>
        )}
      </div>
      <div className="flex shrink-0 items-center gap-2">
        {trailing}
        <SupportTicketCloseButton onClick={onClose} />
      </div>
    </header>
  );
}

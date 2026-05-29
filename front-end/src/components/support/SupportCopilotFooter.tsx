import type { RefObject } from "react";

type Props = {
  input: string;
  loading: boolean;
  inputRef: RefObject<HTMLTextAreaElement | null>;
  onInputChange: (value: string) => void;
  onSubmit: () => void;
  onOpenTicket: () => void;
};

export default function SupportCopilotFooter({
  input,
  loading,
  inputRef,
  onInputChange,
  onSubmit,
  onOpenTicket,
}: Props) {
  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    onSubmit();
  }

  return (
    <div className="shrink-0 space-y-2 border-t border-gray-200/60 p-3 dark:border-white/10">
      <button
        type="button"
        onClick={onOpenTicket}
        disabled={loading}
        className="w-full rounded-xl border border-dashed border-gray-300/80 px-3 py-2 text-xs font-medium text-gray-600 transition hover:border-brand-300 hover:bg-brand-50/50 hover:text-brand-600 disabled:opacity-50 dark:border-gray-600 dark:text-gray-400 dark:hover:border-brand-700 dark:hover:bg-brand-500/10 dark:hover:text-brand-400"
      >
        Ainda preciso de ajuda / Abrir ticket
      </button>
      <form onSubmit={handleSubmit} className="flex gap-2">
        <textarea
          ref={inputRef}
          rows={2}
          value={input}
          onChange={(e) => onInputChange(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              onSubmit();
            }
          }}
          placeholder="Digite sua dúvida…"
          disabled={loading}
          className="min-h-[44px] flex-1 resize-none rounded-xl border border-gray-200/80 bg-white/60 px-3 py-2 text-sm text-gray-800 placeholder:text-gray-400 focus:border-brand-300 focus:outline-hidden focus:ring-2 focus:ring-brand-500/20 disabled:opacity-60 dark:border-gray-700/80 dark:bg-gray-800/60 dark:text-white/90 dark:placeholder:text-gray-500"
        />
        <button
          type="submit"
          disabled={loading || !input.trim()}
          className="shrink-0 self-end rounded-xl bg-brand-500 px-4 py-2 text-sm font-medium text-white hover:bg-brand-600 disabled:cursor-not-allowed disabled:opacity-50"
        >
          Enviar
        </button>
      </form>
    </div>
  );
}

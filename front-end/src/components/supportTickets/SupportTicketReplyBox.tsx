type Props = {
  value: string;
  disabled: boolean;
  sending: boolean;
  closed: boolean;
  onChange: (value: string) => void;
  onSubmit: () => void;
};

export default function SupportTicketReplyBox({
  value,
  disabled,
  sending,
  closed,
  onChange,
  onSubmit,
}: Props) {
  if (closed) {
    return (
      <div className="shrink-0 border-t border-gray-200 px-5 py-4 dark:border-gray-800">
        <p className="text-center text-sm text-gray-500 dark:text-gray-400">
          Este chamado está encerrado e não aceita novas respostas.
        </p>
      </div>
    );
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    onSubmit();
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="shrink-0 border-t border-gray-200 px-5 py-4 dark:border-gray-800"
    >
      <label className="mb-2 block text-xs font-medium text-gray-600 dark:text-gray-400">
        Enviar atualização ao suporte
      </label>
      <textarea
        rows={3}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        disabled={disabled || sending}
        placeholder="Digite informações adicionais…"
        className="w-full resize-y rounded-xl border border-gray-200 bg-gray-50 px-3 py-2 text-sm text-gray-800 placeholder:text-gray-400 focus:border-brand-300 focus:outline-hidden focus:ring-2 focus:ring-brand-500/20 disabled:opacity-60 dark:border-gray-700 dark:bg-gray-800 dark:text-white/90"
      />
      <button
        type="submit"
        disabled={disabled || sending || !value.trim()}
        className="mt-2 w-full rounded-xl bg-brand-500 px-4 py-2 text-sm font-medium text-white hover:bg-brand-600 disabled:cursor-not-allowed disabled:opacity-50"
      >
        {sending ? "Enviando…" : "Enviar resposta"}
      </button>
    </form>
  );
}

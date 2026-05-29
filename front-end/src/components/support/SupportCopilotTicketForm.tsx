type Props = {
  subject: string;
  description: string;
  submitting: boolean;
  onSubjectChange: (value: string) => void;
  onDescriptionChange: (value: string) => void;
  onSubmit: () => void;
  onCancel: () => void;
};

export default function SupportCopilotTicketForm({
  subject,
  description,
  submitting,
  onSubjectChange,
  onDescriptionChange,
  onSubmit,
  onCancel,
}: Props) {
  return (
    <div className="flex min-h-0 flex-1 flex-col gap-4 overflow-y-auto px-4 py-4">
      <p className="text-sm text-gray-600 dark:text-gray-400">
        Descreva o problema. O histórico recente do chat foi incluído na descrição para agilizar o
        atendimento.
      </p>
      <label className="block space-y-1.5">
        <span className="text-xs font-medium text-gray-700 dark:text-gray-300">Assunto</span>
        <input
          type="text"
          value={subject}
          onChange={(e) => onSubjectChange(e.target.value)}
          maxLength={200}
          placeholder="Resumo do problema"
          disabled={submitting}
          className="w-full rounded-xl border border-gray-200/80 bg-white/60 px-3 py-2 text-sm text-gray-800 placeholder:text-gray-400 focus:border-brand-300 focus:outline-hidden focus:ring-2 focus:ring-brand-500/20 disabled:opacity-60 dark:border-gray-700/80 dark:bg-gray-800/60 dark:text-white/90"
        />
      </label>
      <label className="block min-h-0 flex-1 space-y-1.5">
        <span className="text-xs font-medium text-gray-700 dark:text-gray-300">Descrição</span>
        <textarea
          value={description}
          onChange={(e) => onDescriptionChange(e.target.value)}
          rows={10}
          disabled={submitting}
          className="min-h-[180px] w-full resize-y rounded-xl border border-gray-200/80 bg-white/60 px-3 py-2 text-sm text-gray-800 placeholder:text-gray-400 focus:border-brand-300 focus:outline-hidden focus:ring-2 focus:ring-brand-500/20 disabled:opacity-60 dark:border-gray-700/80 dark:bg-gray-800/60 dark:text-white/90"
        />
      </label>
      <div className="flex gap-2 pt-1">
        <button
          type="button"
          onClick={onCancel}
          disabled={submitting}
          className="flex-1 rounded-xl border border-gray-200/80 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50/80 disabled:opacity-50 dark:border-gray-700 dark:text-gray-300 dark:hover:bg-white/5"
        >
          Voltar
        </button>
        <button
          type="button"
          onClick={onSubmit}
          disabled={submitting || !subject.trim() || !description.trim()}
          className="flex-1 rounded-xl bg-brand-500 px-4 py-2 text-sm font-medium text-white hover:bg-brand-600 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {submitting ? "Enviando…" : "Enviar chamado"}
        </button>
      </div>
    </div>
  );
}

import Button from "../../ui/button/Button";

type Props = {
  canManage: boolean;
  busy: boolean;
  onRestart: () => void;
  onDisconnect: () => void;
};

export default function WhatsappActionCenter({ canManage, busy, onRestart, onDisconnect }: Props) {
  if (!canManage) return null;

  return (
    <div className="flex flex-wrap gap-3">
      <Button variant="outline" disabled={busy} onClick={onRestart}>
        {busy ? (
          <span className="inline-flex items-center gap-2">
            <span className="h-4 w-4 animate-spin rounded-full border-2 border-brand-500 border-t-transparent" />
            Reiniciando…
          </span>
        ) : (
          "Reiniciar"
        )}
      </Button>
      <button
        type="button"
        disabled={busy}
        onClick={onDisconnect}
        className="inline-flex items-center justify-center gap-2 rounded-lg bg-error-500 px-5 py-3.5 text-sm text-white shadow-theme-xs transition hover:bg-error-600 disabled:cursor-not-allowed disabled:opacity-50"
      >
        Desconectar
      </button>
    </div>
  );
}

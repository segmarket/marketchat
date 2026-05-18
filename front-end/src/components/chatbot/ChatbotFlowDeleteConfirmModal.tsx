import { Modal } from "../ui/modal";
import Button from "../ui/button/Button";

type Props = {
  isOpen: boolean;
  busy: boolean;
  flowName?: string;
  onClose: () => void;
  onConfirm: () => void;
};

export default function ChatbotFlowDeleteConfirmModal({
  isOpen,
  busy,
  flowName,
  onClose,
  onConfirm,
}: Props) {
  return (
    <Modal isOpen={isOpen} onClose={onClose} className="max-w-md p-6">
      <h3 className="text-lg font-semibold text-gray-900 dark:text-white/90">Excluir fluxo?</h3>
      <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">
        {flowName ? (
          <>
            O fluxo <span className="font-medium text-gray-800 dark:text-white/90">{flowName}</span> será
            removido permanentemente.
          </>
        ) : (
          "Este fluxo será removido permanentemente."
        )}
      </p>
      <div className="mt-6 flex flex-wrap justify-end gap-3">
        <Button variant="outline" onClick={onClose} disabled={busy}>
          Cancelar
        </Button>
        <button
          type="button"
          disabled={busy}
          onClick={onConfirm}
          className="inline-flex items-center justify-center rounded-lg bg-error-500 px-5 py-3.5 text-sm text-white hover:bg-error-600 disabled:opacity-50"
        >
          {busy ? "Excluindo…" : "Excluir"}
        </button>
      </div>
    </Modal>
  );
}

import { Modal } from "../ui/modal";
import Button from "../ui/button/Button";

type Props = {
  isOpen: boolean;
  busy: boolean;
  marketName?: string;
  onClose: () => void;
  onConfirm: () => void;
};

export default function MarketDeleteConfirmModal({
  isOpen,
  busy,
  marketName,
  onClose,
  onConfirm,
}: Props) {
  return (
    <Modal isOpen={isOpen} onClose={onClose} className="max-w-md p-6">
      <h3 className="text-lg font-semibold text-gray-900 dark:text-white/90">Remover mercado?</h3>
      <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">
        Tem certeza que deseja remover este mercado?
        {marketName ? (
          <>
            {" "}
            <span className="font-medium text-gray-800 dark:text-white/90">{marketName}</span> será
            excluído permanentemente.
          </>
        ) : null}
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
          {busy ? "Removendo…" : "Excluir"}
        </button>
      </div>
    </Modal>
  );
}

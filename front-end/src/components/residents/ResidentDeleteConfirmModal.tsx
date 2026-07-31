import { Modal } from "../ui/modal";
import Button from "../ui/button/Button";
import type { Resident } from "../../features/residents/types";

type Props = {
  resident: Resident | null;
  isOpen: boolean;
  busy: boolean;
  onClose: () => void;
  onConfirm: () => void;
};

export default function ResidentDeleteConfirmModal({
  resident,
  isOpen,
  busy,
  onClose,
  onConfirm,
}: Props) {
  const name = resident?.name?.trim() || "este morador";

  return (
    <Modal isOpen={isOpen} onClose={onClose} className="max-w-md p-6">
      <h3 className="text-lg font-semibold text-gray-900 dark:text-white/90">
        Excluir morador?
      </h3>
      <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">
        Tem certeza que deseja excluir o morador{" "}
        <span className="font-medium text-gray-800 dark:text-white/90">{name}</span>? Esta ação
        não poderá ser desfeita.
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

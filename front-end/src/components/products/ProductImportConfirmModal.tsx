import { Modal } from "../ui/modal";
import Button from "../ui/button/Button";
import type { ImportPreviewResponse } from "../../features/products/types";

type Props = {
  isOpen: boolean;
  preview: ImportPreviewResponse | null;
  busy: boolean;
  onClose: () => void;
  onConfirm: () => void;
};

export default function ProductImportConfirmModal({
  isOpen,
  preview,
  busy,
  onClose,
  onConfirm,
}: Props) {
  const newCount = preview?.new_count ?? 0;
  const updatedCount = preview?.updated_count ?? 0;

  return (
    <Modal isOpen={isOpen} onClose={onClose} className="max-w-lg p-6">
      <h3 className="text-lg font-semibold text-gray-900 dark:text-white/90">
        Confirmar Importação de Produtos
      </h3>
      <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">
        Revise o resumo abaixo antes de aplicar as alterações no catálogo.
      </p>

      <div className="mt-6 grid gap-4 sm:grid-cols-2">
        <div className="rounded-xl border border-success-200 bg-success-50 p-4 dark:border-success-900/40 dark:bg-success-950/30">
          <p className="text-2xl font-semibold text-success-700 dark:text-success-400">
            {newCount}
          </p>
          <p className="mt-1 text-sm text-success-800 dark:text-success-300">
            {newCount === 1
              ? "novo produto identificado para cadastro"
              : "novos produtos identificados para cadastro"}
          </p>
        </div>
        <div className="rounded-xl border border-warning-200 bg-warning-50 p-4 dark:border-warning-900/40 dark:bg-warning-950/30">
          <p className="text-2xl font-semibold text-warning-700 dark:text-warning-400">
            {updatedCount}
          </p>
          <p className="mt-1 text-sm text-warning-800 dark:text-warning-300">
            {updatedCount === 1
              ? "produto existente será atualizado"
              : "produtos existentes serão atualizados"}
          </p>
        </div>
      </div>

      {newCount === 0 && updatedCount === 0 && (
        <p className="mt-4 text-sm text-gray-500 dark:text-gray-400">
          Nenhuma alteração detectada na planilha em relação ao catálogo atual.
        </p>
      )}

      <div className="mt-6 flex flex-wrap justify-end gap-3">
        <Button variant="outline" onClick={onClose} disabled={busy}>
          Cancelar
        </Button>
        <Button onClick={onConfirm} disabled={busy || (!newCount && !updatedCount)}>
          {busy ? "Importando…" : "Confirmar Atualização"}
        </Button>
      </div>
    </Modal>
  );
}

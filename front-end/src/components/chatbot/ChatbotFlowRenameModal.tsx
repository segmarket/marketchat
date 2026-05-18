import { useEffect, useState } from "react";
import Button from "../ui/button/Button";
import { Modal } from "../ui/modal";

type Props = {
  isOpen: boolean;
  busy: boolean;
  initialName: string;
  onClose: () => void;
  onConfirm: (name: string) => void;
};

export default function ChatbotFlowRenameModal({
  isOpen,
  busy,
  initialName,
  onClose,
  onConfirm,
}: Props) {
  const [name, setName] = useState(initialName);

  useEffect(() => {
    if (isOpen) setName(initialName);
  }, [isOpen, initialName]);

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const trimmed = name.trim();
    if (!trimmed) return;
    onConfirm(trimmed);
  }

  return (
    <Modal isOpen={isOpen} onClose={onClose} className="max-w-md p-6">
      <h3 className="text-lg font-semibold text-gray-900 dark:text-white/90">Renomear fluxo</h3>
      <form onSubmit={handleSubmit} className="mt-4 space-y-4">
        <div>
          <label className="mb-1.5 block text-sm font-medium text-gray-700 dark:text-gray-300">
            Nome do fluxo
          </label>
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="h-11 w-full rounded-lg border border-gray-300 px-3 text-sm focus:border-brand-300 focus:outline-none focus:ring-2 focus:ring-brand-500/30 dark:border-gray-700 dark:bg-gray-800 dark:text-white/90"
            autoFocus
          />
        </div>
        <div className="flex justify-end gap-3">
          <Button type="button" variant="outline" onClick={onClose} disabled={busy}>
            Cancelar
          </Button>
          <Button type="submit" disabled={busy || !name.trim()}>
            {busy ? "Salvando…" : "Salvar"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}

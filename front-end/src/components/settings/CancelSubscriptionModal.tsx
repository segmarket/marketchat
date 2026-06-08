import { useState } from "react";
import { toast } from "sonner";
import { Modal } from "../ui/modal";
import Button from "../ui/button/Button";
import { cancelSubscription } from "../../features/settings/api";
import { getAxiosErrorMessage } from "../../utils/apiError";

type CancelSubscriptionModalProps = {
  isOpen: boolean;
  onClose: () => void;
  trialEndsAt?: string | null;
  onSuccess: () => void;
};

export default function CancelSubscriptionModal({
  isOpen,
  onClose,
  trialEndsAt,
  onSuccess,
}: CancelSubscriptionModalProps) {
  const [submitting, setSubmitting] = useState(false);

  const handleConfirm = async () => {
    setSubmitting(true);
    try {
      await cancelSubscription();
      toast.success("Assinatura cancelada com sucesso.");
      onSuccess();
      onClose();
    } catch (e: unknown) {
      toast.error(getAxiosErrorMessage(e));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} className="max-w-md p-6">
      <h3 className="mb-2 text-lg font-semibold text-gray-900 dark:text-white">
        Cancelar assinatura
      </h3>
      <p className="mb-4 text-sm text-gray-600 dark:text-gray-400">
        Ao confirmar, não haverá novas cobranças no cartão cadastrado.
        {trialEndsAt
          ? " Você continua com acesso ao painel até o fim do período de testes."
          : " O acesso ao painel será encerrado conforme o plano contratado."}
      </p>
      <div className="flex flex-col-reverse gap-3 sm:flex-row sm:justify-end">
        <Button variant="outline" className="min-h-[44px]" onClick={onClose} disabled={submitting}>
          Voltar
        </Button>
        <Button
          variant="primary"
          className="min-h-[44px]"
          onClick={() => void handleConfirm()}
          disabled={submitting}
        >
          {submitting ? "Cancelando…" : "Confirmar cancelamento"}
        </Button>
      </div>
    </Modal>
  );
}

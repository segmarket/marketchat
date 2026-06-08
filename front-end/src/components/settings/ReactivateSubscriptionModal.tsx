import { useState } from "react";
import axios from "axios";
import { toast } from "sonner";
import { Modal } from "../ui/modal";
import Button from "../ui/button/Button";
import { reactivateSubscription } from "../../features/settings/api";
import { getAxiosErrorMessage } from "../../utils/apiError";

const CARD_REQUIRED_MESSAGE =
  "Não foi possível reativar com o cartão atual. Por favor, insira um novo cartão de crédito para reativar seu plano.";

type ReactivateSubscriptionModalProps = {
  isOpen: boolean;
  onClose: () => void;
  monthlyTotal: number;
  cardLastFour: string | null;
  onSuccess: () => void;
  onCardRequired: () => void;
};

function formatBRL(value: number): string {
  return value.toFixed(2).replace(".", ",");
}

export default function ReactivateSubscriptionModal({
  isOpen,
  onClose,
  monthlyTotal,
  cardLastFour,
  onSuccess,
  onCardRequired,
}: ReactivateSubscriptionModalProps) {
  const [submitting, setSubmitting] = useState(false);

  const handleConfirm = async () => {
    setSubmitting(true);
    try {
      await reactivateSubscription();
      toast.success("Assinatura reativada com sucesso.");
      onSuccess();
      onClose();
    } catch (e: unknown) {
      if (axios.isAxiosError(e)) {
        const status = e.response?.status;
        const code = e.response?.data?.code;
        if (status === 402 || code === "card_required") {
          toast.error(CARD_REQUIRED_MESSAGE);
          onClose();
          onCardRequired();
          return;
        }
      }
      toast.error(getAxiosErrorMessage(e));
    } finally {
      setSubmitting(false);
    }
  };

  const cardHint = cardLastFour
    ? `cartão final ${cardLastFour}`
    : "cartão cadastrado";

  return (
    <Modal isOpen={isOpen} onClose={onClose} className="max-w-md p-6">
      <h3 className="mb-2 text-lg font-semibold text-gray-900 dark:text-white">
        Confirmar reativação?
      </h3>
      <p className="mb-4 text-sm text-gray-600 dark:text-gray-400">
        Sua assinatura será reativada usando o {cardHint}, no valor de R$ {formatBRL(monthlyTotal)}
        /mês conforme seus mercados ativos.
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
          {submitting ? "Reativando…" : "Confirmar reativação"}
        </Button>
      </div>
    </Modal>
  );
}

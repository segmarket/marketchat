import { Modal } from "../ui/modal";
import type { AccountSettingsResponse, PaymentMethodSummary } from "../../features/settings/types";
import UpdateCardForm from "./UpdateCardForm";

type UpdateCardModalProps = {
  isOpen: boolean;
  onClose: () => void;
  accountData: AccountSettingsResponse;
  onSuccess: (summary: PaymentMethodSummary) => void;
};

export default function UpdateCardModal({ isOpen, onClose, accountData, onSuccess }: UpdateCardModalProps) {
  return (
    <Modal isOpen={isOpen} onClose={onClose} className="max-w-[700px] m-4">
      <div className="p-6 sm:p-8">
        <h3 className="mb-2 text-xl font-semibold text-gray-800 dark:text-white/90">Alterar cartão</h3>
        <p className="mb-6 text-sm text-gray-500 dark:text-gray-400">
          Os dados são enviados de forma segura ao provedor de pagamentos.
        </p>
        <UpdateCardForm
          accountData={accountData}
          onSuccess={onSuccess}
          showCancel
          onCancel={onClose}
        />
      </div>
    </Modal>
  );
}

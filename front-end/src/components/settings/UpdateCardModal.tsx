import { Modal } from "../ui/modal";
import type {
  AccountSettingsResponse,
  PaymentMethodSummary,
  RegularizeResponse,
  RequiredCharge,
} from "../../features/settings/types";
import RequiredChargesNotice from "../billing/RequiredChargesNotice";
import UpdateCardForm from "./UpdateCardForm";

type UpdateCardModalProps = {
  isOpen: boolean;
  onClose: () => void;
  accountData: AccountSettingsResponse;
  mode?: "update" | "regularize";
  requiredCharges?: RequiredCharge[];
  onSuccess?: (summary: PaymentMethodSummary) => void;
  onRegularized?: (result: RegularizeResponse) => void;
};

export default function UpdateCardModal({
  isOpen,
  onClose,
  accountData,
  mode = "update",
  requiredCharges = [],
  onSuccess,
  onRegularized,
}: UpdateCardModalProps) {
  const regularize = mode === "regularize";
  return (
    <Modal isOpen={isOpen} onClose={onClose} className="max-w-[700px] m-4">
      <div className="p-6 sm:p-8">
        <h3 className="mb-2 text-xl font-semibold text-gray-800 dark:text-white/90">
          {regularize ? "Pagar fatura em aberto" : "Alterar cartão"}
        </h3>
        <p className="mb-6 text-sm text-gray-500 dark:text-gray-400">
          {regularize
            ? "A fatura em aberto será cobrada agora neste cartão, que também passa a ser usado nas próximas mensalidades."
            : "O novo cartão vale para as próximas cobranças. Trocar o cartão não paga uma fatura já vencida."}{" "}
          Os dados são enviados de forma segura ao provedor de pagamentos.
        </p>
        {regularize && <RequiredChargesNotice charges={requiredCharges} className="mb-6" />}
        <UpdateCardForm
          accountData={accountData}
          mode={mode}
          submitLabel={regularize ? "Pagar fatura agora" : "Salvar cartão"}
          onSuccess={onSuccess}
          onRegularized={onRegularized}
          showCancel
          onCancel={onClose}
        />
      </div>
    </Modal>
  );
}

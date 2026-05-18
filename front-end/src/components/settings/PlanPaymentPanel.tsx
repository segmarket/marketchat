import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";
import axios from "axios";
import Badge from "../ui/badge/Badge";
import Button from "../ui/button/Button";
import FormSection from "../layout/FormSection";
import { useAuth } from "../../context/AuthContext";
import { fetchPaymentMethod } from "../../features/settings/api";
import type { AccountSettingsResponse, PaymentMethodSummary } from "../../features/settings/types";
import { getAxiosErrorMessage } from "../../utils/apiError";
import CreditCardDisplay from "./CreditCardDisplay";
import UpdateCardModal from "./UpdateCardModal";
import { useModal } from "../../hooks/useModal";

const PLAN_PRICE = import.meta.env.VITE_TRIAL_SUBSCRIPTION_PRICE ?? "29,90";

type PlanPaymentPanelProps = {
  accountData: AccountSettingsResponse;
};

export default function PlanPaymentPanel({ accountData }: PlanPaymentPanelProps) {
  const { user } = useAuth();
  const { isOpen, openModal, closeModal } = useModal();
  const [summary, setSummary] = useState<PaymentMethodSummary | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await fetchPaymentMethod();
      setSummary(data);
    } catch (e: unknown) {
      setSummary(null);
      if (axios.isAxiosError(e) && e.response?.status === 502) {
        toast.error("Serviço de pagamentos temporariamente indisponível.");
      } else if (axios.isAxiosError(e) && e.response?.status === 403) {
        toast.error("Apenas administradores podem acessar cobrança.");
      } else {
        toast.error(getAxiosErrorMessage(e));
      }
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const blocked = user?.billing_blocked ?? false;

  return (
    <div className="space-y-8">
      <FormSection
        title="Plano MarketChat"
        description={`Assinatura mensal do MarketChat — R$ ${PLAN_PRICE} por mês.`}
      >
        <div className="flex flex-wrap items-center gap-3">
          <span className="text-lg font-semibold text-gray-800 dark:text-white/90">Plano Pro</span>
          <Badge color={blocked ? "error" : "success"} size="sm">
            {blocked ? "Em atraso" : "Ativo"}
          </Badge>
        </div>
      </FormSection>

      <FormSection
        title="Forma de pagamento"
        description="Cartão ou método usado para cobrança recorrente da assinatura."
      >
        {loading ? (
          <p className="text-sm text-gray-500 animate-pulse">Carregando…</p>
        ) : summary ? (
          <div className="space-y-6">
            {summary.billing_type === "CREDIT_CARD" ? (
              <CreditCardDisplay summary={summary} />
            ) : (
              <p className="text-sm text-gray-700 dark:text-gray-300">{summary.display_label}</p>
            )}
            {summary.billing_type === "CREDIT_CARD" && (
              <div className="flex justify-end border-t border-gray-100 pt-4 dark:border-gray-800">
                <Button variant="outline" onClick={openModal}>
                  Alterar cartão de crédito
                </Button>
              </div>
            )}
          </div>
        ) : (
          <p className="text-sm text-gray-500">Não foi possível carregar a forma de pagamento.</p>
        )}
      </FormSection>

      <UpdateCardModal
        isOpen={isOpen}
        onClose={closeModal}
        accountData={accountData}
        onSuccess={(s) => {
          setSummary(s);
          closeModal();
        }}
      />
    </div>
  );
}

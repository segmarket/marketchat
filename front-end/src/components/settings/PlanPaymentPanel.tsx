import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";
import axios from "axios";
import Badge from "../ui/badge/Badge";
import Button from "../ui/button/Button";
import FormSection from "../layout/FormSection";
import { useAuth } from "../../context/AuthContext";
import { fetchPaymentMethod } from "../../features/settings/api";
import type {
  AccountSettingsResponse,
  PaymentMethodSummary,
  TenantSubscriptionStatus,
} from "../../features/settings/types";
import { formatDateBR } from "../../features/settings/format";
import { getAxiosErrorMessage } from "../../utils/apiError";
import CreditCardDisplay from "./CreditCardDisplay";
import UpdateCardModal from "./UpdateCardModal";
import CancelSubscriptionModal from "./CancelSubscriptionModal";
import ReactivateSubscriptionModal from "./ReactivateSubscriptionModal";
import { useModal } from "../../hooks/useModal";

const PLAN_PRICE = import.meta.env.VITE_PLAN_PRICE?.trim() || "59,90";

type PlanPaymentPanelProps = {
  accountData: AccountSettingsResponse;
};

function resolveStatus(
  summary: PaymentMethodSummary | null,
  userStatus: TenantSubscriptionStatus | undefined,
): TenantSubscriptionStatus | undefined {
  return summary?.subscription_status ?? userStatus;
}

function planBadge(
  status: TenantSubscriptionStatus | undefined,
  billingBlocked: boolean,
  inGrace: boolean,
  summary: PaymentMethodSummary | null,
): { label: string; color: "success" | "warning" | "error" } {
  if (status === "CANCELED" || summary?.subscription_canceled) {
    return { label: "Inativa", color: "error" };
  }
  if (status === "OVERDUE" && (inGrace || summary?.is_in_grace_period)) {
    return { label: "Em carência", color: "warning" };
  }
  if (status === "OVERDUE") {
    return { label: "Pagamento em atraso", color: "error" };
  }
  if (billingBlocked || status === "SUSPENDED") {
    return { label: "Suspensa", color: "error" };
  }
  if (summary?.in_trial_period || status === "TRIAL") {
    return { label: "Período de testes", color: "warning" };
  }
  return { label: "Ativa", color: "success" };
}

export default function PlanPaymentPanel({ accountData }: PlanPaymentPanelProps) {
  const { user, refreshUser } = useAuth();
  const cardModal = useModal();
  const cancelModal = useModal();
  const reactivateModal = useModal();
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
  const inGrace = user?.is_in_grace_period ?? false;
  const status = resolveStatus(
    summary,
    user?.subscription_status as TenantSubscriptionStatus | undefined,
  );
  const badge = planBadge(status, blocked, inGrace, summary);
  const unitPrice = summary?.unit_price ?? 59.9;
  const marketCount = summary?.active_markets_count ?? 0;
  const monthlyTotal = summary?.monthly_total ?? 0;

  const isCanceled = status === "CANCELED" || summary?.subscription_canceled === true;
  const isOverdue = status === "OVERDUE";
  const canReactivate = summary?.can_reactivate ?? (isCanceled && marketCount > 0);

  const subscriptionNote = (() => {
    if (!summary) return null;
    if (isCanceled) {
      if (summary.in_trial_period && summary.trial_ends_at) {
        return `Assinatura inativa. Você mantém acesso até ${formatDateBR(summary.trial_ends_at)} e não será cobrado.`;
      }
      return "Sua assinatura está inativa. Não há cobranças programadas no momento.";
    }
    if (isOverdue) {
      return null;
    }
    if (summary.is_in_grace_period || inGrace) {
      return "Houve falha na cobrança da mensalidade. Atualize o cartão para evitar a suspensão dos atendimentos do WhatsApp.";
    }
    if (summary.in_trial_period) {
      const chargeDate = summary.next_due_date
        ? formatDateBR(summary.next_due_date)
        : summary.trial_ends_at
          ? formatDateBR(summary.trial_ends_at)
          : null;
      if (chargeDate) {
        return `Cartão cadastrado para cobrança automática a partir de ${chargeDate}. Se não quiser continuar, cancele a assinatura antes dessa data.`;
      }
      return "Cartão cadastrado. A cobrança ocorrerá automaticamente ao fim do período de testes, salvo cancelamento.";
    }
    if (summary.next_due_date) {
      return `Próxima cobrança prevista para ${formatDateBR(summary.next_due_date)}.`;
    }
    return null;
  })();

  const handleBillingRefresh = () => {
    void load();
    void refreshUser();
  };

  return (
    <div className="space-y-8">
      {isOverdue && (
        <div
          role="alert"
          className="rounded-xl border border-red-200 bg-red-50 p-5 dark:border-red-900/50 dark:bg-red-950/30"
        >
          <p className="text-sm font-semibold text-red-800 dark:text-red-200">
            Falha na cobrança automática
          </p>
          <p className="mt-2 text-sm text-red-700 dark:text-red-300/90">
            Não conseguimos processar o pagamento recorrente no seu cartão cadastrado. Seu sistema
            está operando em modo de carência.
          </p>
          <div className="mt-4">
            <Button variant="primary" onClick={cardModal.openModal}>
              Atualizar cartão e tentar novamente
            </Button>
          </div>
        </div>
      )}

      {isCanceled && canReactivate && (
        <div
          className="rounded-xl border border-slate-200 bg-slate-50 p-6 dark:border-slate-700 dark:bg-slate-900/40"
        >
          <p className="text-sm font-medium text-slate-800 dark:text-slate-100">
            Sua assinatura está inativa.
          </p>
          <p className="mt-2 text-sm text-slate-600 dark:text-slate-400">
            Seus robôs do WhatsApp foram pausados e os dashboards congelados. Deseja voltar a
            monitorar seus mercados?
          </p>
          <div className="mt-4">
            <Button variant="primary" onClick={reactivateModal.openModal}>
              Reativar minha assinatura
            </Button>
          </div>
        </div>
      )}

      <FormSection
        title="Plano MarketChat"
        description={
          marketCount > 0
            ? `${marketCount} mercado(s) ativo(s) × R$ ${unitPrice.toFixed(2).replace(".", ",")} = R$ ${monthlyTotal.toFixed(2).replace(".", ",")}/mês.`
            : `R$ ${PLAN_PRICE} por mercado ativo por mês.`
        }
      >
        <div className="space-y-3">
          <div className="flex flex-wrap items-center gap-3">
            <span className="text-lg font-semibold text-gray-800 dark:text-white/90">Plano Pro</span>
            <Badge color={badge.color} size="sm">
              {badge.label}
            </Badge>
          </div>
          {subscriptionNote && (
            <p className="text-sm text-gray-600 dark:text-gray-400">{subscriptionNote}</p>
          )}
        </div>
      </FormSection>

      <FormSection
        title="Forma de pagamento"
        description="Cartão usado para cobrança recorrente da assinatura."
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
            <div className="flex flex-wrap justify-end gap-3 border-t border-gray-100 pt-4 dark:border-gray-800">
              {summary.can_cancel && !isCanceled && (
                <Button variant="outline" onClick={cancelModal.openModal}>
                  Cancelar assinatura
                </Button>
              )}
              {summary.billing_type === "CREDIT_CARD" && !isCanceled && (
                <Button variant="outline" onClick={cardModal.openModal}>
                  Alterar cartão de crédito
                </Button>
              )}
              {isCanceled && summary.billing_type === "CREDIT_CARD" && (
                <Button variant="outline" onClick={cardModal.openModal}>
                  Cadastrar novo cartão
                </Button>
              )}
            </div>
          </div>
        ) : (
          <p className="text-sm text-gray-500">Não foi possível carregar a forma de pagamento.</p>
        )}
      </FormSection>

      <UpdateCardModal
        isOpen={cardModal.isOpen}
        onClose={cardModal.closeModal}
        accountData={accountData}
        onSuccess={(s) => {
          setSummary(s);
          cardModal.closeModal();
          void refreshUser();
        }}
      />

      <CancelSubscriptionModal
        isOpen={cancelModal.isOpen}
        onClose={cancelModal.closeModal}
        trialEndsAt={summary?.in_trial_period ? summary.trial_ends_at : null}
        onSuccess={handleBillingRefresh}
      />

      <ReactivateSubscriptionModal
        isOpen={reactivateModal.isOpen}
        onClose={reactivateModal.closeModal}
        monthlyTotal={monthlyTotal > 0 ? monthlyTotal : unitPrice}
        cardLastFour={summary?.card_last_four ?? null}
        onSuccess={handleBillingRefresh}
        onCardRequired={cardModal.openModal}
      />
    </div>
  );
}

import type { SubscriptionImpact } from "../../features/billing/subscriptionImpact";
import { formatCurrencyBRL } from "../../features/settings/format";
import { Modal } from "../ui/modal";
import Button from "../ui/button/Button";

type Props = {
  isOpen: boolean;
  busy: boolean;
  impact: SubscriptionImpact;
  inTrial: boolean;
  onClose: () => void;
  onConfirm: () => void;
};

function marketLabel(count: number): string {
  return count === 1 ? "1 mercado" : `${count} mercados`;
}

export default function MarketSubscriptionConfirmModal({
  isOpen,
  busy,
  impact,
  inTrial,
  onClose,
  onConfirm,
}: Props) {
  const unitFormatted = formatCurrencyBRL(impact.unitPrice);
  const currentFormatted = formatCurrencyBRL(impact.currentTotal);
  const projectedFormatted = formatCurrencyBRL(impact.projectedTotal);

  return (
    <Modal isOpen={isOpen} onClose={onClose} className="max-w-md p-6">
      <h3 className="text-lg font-semibold text-gray-900 dark:text-white/90">
        Alteração na assinatura
      </h3>
      <p className="mt-3 text-sm text-gray-600 dark:text-gray-400">
        Ao cadastrar este mercado como ativo, sua mensalidade passará de{" "}
        <span className="font-medium text-gray-800 dark:text-white/90">
          {currentFormatted}/mês
        </span>{" "}
        ({marketLabel(impact.activeCount)}) para{" "}
        <span className="font-medium text-gray-800 dark:text-white/90">
          {projectedFormatted}/mês
        </span>{" "}
        ({marketLabel(impact.projectedCount)}).
      </p>
      <p className="mt-2 text-sm text-gray-500 dark:text-gray-400">
        {unitFormatted} por mercado ativo por mês.
      </p>
      <p className="mt-4 text-sm text-gray-600 dark:text-gray-400">
        {inTrial
          ? "Você está no período de testes. O novo valor será considerado na cobrança após o fim dos 7 dias grátis."
          : "A mensalidade será ajustada automaticamente na sua assinatura."}
      </p>
      <div className="mt-6 flex flex-wrap justify-end gap-3">
        <Button type="button" variant="outline" onClick={onClose} disabled={busy}>
          Cancelar
        </Button>
        <Button type="button" onClick={onConfirm} disabled={busy}>
          {busy ? "Cadastrando…" : "Confirmar e cadastrar"}
        </Button>
      </div>
    </Modal>
  );
}

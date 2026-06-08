import { Clock, Wallet } from "lucide-react";
import Button from "../ui/button/Button";
import { formatBRL } from "../../features/financial/format";

type Props = {
  balanceAvailable: string;
  balanceProcessing: string;
  loading?: boolean;
  canWithdraw: boolean;
  onWithdrawClick: () => void;
};

export default function FinancialSummaryCards({
  balanceAvailable,
  balanceProcessing,
  loading = false,
  canWithdraw,
  onWithdrawClick,
}: Props) {
  if (loading) {
    return (
      <div className="mb-6 grid grid-cols-1 gap-4 md:grid-cols-2">
        {[1, 2].map((i) => (
          <div
            key={i}
            className="h-36 animate-pulse rounded-2xl border border-gray-200 bg-gray-50 dark:border-gray-800 dark:bg-white/5"
          />
        ))}
      </div>
    );
  }

  return (
    <div className="mb-6 grid grid-cols-1 gap-4 md:grid-cols-2">
      <div className="rounded-2xl border border-green-200 bg-green-50 p-5 shadow-sm dark:border-green-900/40 dark:bg-green-950/20 md:p-6">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
          <div className="min-w-0 flex-1">
            <p className="text-xs font-semibold uppercase tracking-wide text-green-700 dark:text-green-400">
              Saldo disponível para saque
            </p>
            <p className="mt-3 text-2xl font-bold text-green-800 md:text-3xl dark:text-green-300">
              {formatBRL(balanceAvailable)}
            </p>
            <Button
              className="mt-5 min-h-[44px] w-full md:w-auto"
              onClick={onWithdrawClick}
              disabled={!canWithdraw}
            >
              Solicitar Saque via Pix
            </Button>
            {!canWithdraw ? (
              <p className="mt-3 text-sm text-amber-700 dark:text-amber-400">
                Configure sua Chave Pix antes de solicitar um saque.
              </p>
            ) : null}
          </div>
          <div className="rounded-xl bg-green-100 p-3 text-green-700 dark:bg-green-900/30 dark:text-green-400">
            <Wallet className="size-6" />
          </div>
        </div>
      </div>

      <div className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm dark:border-gray-800 dark:bg-white/[0.03] md:p-6">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400">
              Em processamento
            </p>
            <p className="mt-3 text-2xl font-bold text-gray-800 md:text-3xl dark:text-white/90">
              {formatBRL(balanceProcessing)}
            </p>
            <p className="mt-2 text-sm text-gray-500 dark:text-gray-400">
              Saques Pix aguardando confirmação bancária no Asaas.
            </p>
          </div>
          <div className="rounded-xl bg-gray-50 p-3 text-gray-500 dark:bg-white/5">
            <Clock className="size-6" />
          </div>
        </div>
      </div>
    </div>
  );
}

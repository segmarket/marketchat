import type { RequiredCharge } from "../../features/settings/types";
import { formatCurrencyBRL, formatDateBR } from "../../features/settings/format";

type RequiredChargesNoticeProps = {
  charges: RequiredCharge[];
  className?: string;
};

export default function RequiredChargesNotice({ charges, className = "" }: RequiredChargesNoticeProps) {
  if (charges.length === 0) {
    return null;
  }
  return (
    <div
      className={`rounded-lg border border-gray-200 bg-gray-50 p-4 text-sm text-gray-700 dark:border-gray-800 dark:bg-gray-900/40 dark:text-gray-300 ${className}`}
    >
      <p className="font-medium">
        {charges.length === 1 ? "Fatura a ser paga agora:" : "Faturas a serem pagas agora:"}
      </p>
      <ul className="mt-2 space-y-1">
        {charges.map((charge) => (
          <li key={charge.id}>
            Vencimento {charge.due_date ? formatDateBR(charge.due_date) : "—"}
            {charge.value !== null ? ` · ${formatCurrencyBRL(charge.value)}` : ""}
          </li>
        ))}
      </ul>
      <p className="mt-2 text-xs text-gray-500 dark:text-gray-400">
        Juros e multa por atraso, se houver, são calculados pelo provedor de pagamentos.
      </p>
    </div>
  );
}

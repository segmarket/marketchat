import Button from "../ui/button/Button";
import { formatBRL, formatLedgerDate } from "../../features/financial/format";
import type { LedgerRow } from "../../features/financial/types";

type Props = {
  rows: LedgerRow[];
  loading?: boolean;
  page: number;
  nextPage: number | null;
  prevPage: number | null;
  totalCount: number;
  onPageChange: (page: number) => void;
};

export default function FinancialStatementTable({
  rows,
  loading = false,
  page,
  nextPage,
  prevPage,
  totalCount,
  onPageChange,
}: Props) {
  if (loading) {
    return (
      <div className="rounded-2xl border border-gray-200 bg-white p-6 dark:border-gray-800 dark:bg-white/[0.03]">
        <div className="h-48 animate-pulse rounded-xl bg-gray-50 dark:bg-white/5" />
      </div>
    );
  }

  return (
    <div className="rounded-2xl border border-gray-200 bg-white shadow-sm dark:border-gray-800 dark:bg-white/[0.03]">
      <div className="border-b border-gray-200 px-5 py-4 dark:border-gray-800">
        <h2 className="text-base font-semibold text-gray-900 dark:text-white/90">Extrato</h2>
        <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
          {totalCount} movimentação(ões)
        </p>
      </div>

      {rows.length === 0 ? (
        <p className="px-5 py-10 text-center text-sm text-gray-500 dark:text-gray-400">
          Nenhuma movimentação ainda. As vendas via Pix aparecerão aqui após a confirmação do
          pagamento.
        </p>
      ) : (
        <div className="overflow-x-auto">
          <table className="min-w-full text-left text-sm">
            <thead className="border-b border-gray-200 bg-gray-50/80 text-xs uppercase tracking-wide text-gray-500 dark:border-gray-800 dark:bg-white/[0.02]">
              <tr>
                <th className="px-5 py-3 font-medium">Data</th>
                <th className="px-5 py-3 font-medium">Descrição</th>
                <th className="px-5 py-3 font-medium">Tipo</th>
                <th className="px-5 py-3 font-medium text-right">Valor</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200 dark:divide-gray-800">
              {rows.map((row) => {
                const isInflow = row.entry_type === "INFLOW";
                return (
                  <tr key={row.id} className="hover:bg-gray-50/50 dark:hover:bg-white/[0.02]">
                    <td className="whitespace-nowrap px-5 py-4 text-gray-600 dark:text-gray-400">
                      {formatLedgerDate(row.created_at)}
                    </td>
                    <td className="px-5 py-4 text-gray-800 dark:text-white/90">{row.description}</td>
                    <td className="px-5 py-4 text-gray-600 dark:text-gray-400">
                      {row.entry_type_label}
                    </td>
                    <td
                      className={`whitespace-nowrap px-5 py-4 text-right font-medium ${
                        isInflow
                          ? "text-emerald-600 dark:text-emerald-400"
                          : "text-gray-800 dark:text-white/90"
                      }`}
                    >
                      {isInflow ? "+" : "-"}
                      {formatBRL(row.amount)}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {(prevPage || nextPage) && (
        <div className="flex items-center justify-between border-t border-gray-200 px-5 py-4 dark:border-gray-800">
          <Button
            type="button"
            variant="outline"
            disabled={!prevPage}
            onClick={() => prevPage && onPageChange(prevPage)}
          >
            Anterior
          </Button>
          <span className="text-sm text-gray-500">Página {page}</span>
          <Button
            type="button"
            variant="outline"
            disabled={!nextPage}
            onClick={() => nextPage && onPageChange(nextPage)}
          >
            Próxima
          </Button>
        </div>
      )}
    </div>
  );
}

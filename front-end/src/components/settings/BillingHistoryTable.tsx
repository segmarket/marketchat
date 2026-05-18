import { useEffect, useState } from "react";
import { toast } from "sonner";
import axios from "axios";
import { Table, TableBody, TableCell, TableHeader, TableRow } from "../ui/table";
import FormSection from "../layout/FormSection";
import { DownloadIcon } from "../../icons";
import { fetchBillingHistory } from "../../features/settings/api";
import type { BillingHistoryItem } from "../../features/settings/types";
import { billingTypeLabel, formatCurrencyBRL, formatDateBR } from "../../features/settings/format";
import { getAxiosErrorMessage } from "../../utils/apiError";
import InvoiceStatusBadge from "./InvoiceStatusBadge";

export default function BillingHistoryTable() {
  const [items, setItems] = useState<BillingHistoryItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      try {
        const data = await fetchBillingHistory();
        if (!cancelled) setItems(data.results);
      } catch (e: unknown) {
        if (!cancelled) {
          if (axios.isAxiosError(e) && e.response?.status === 502) {
            toast.error("Serviço de pagamentos temporariamente indisponível.");
          } else {
            toast.error(getAxiosErrorMessage(e));
          }
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, []);

  return (
    <FormSection title="Histórico de faturas" description="Cobranças e faturas da sua assinatura MarketChat.">
      {loading ? (
        <p className="text-sm text-gray-500 animate-pulse">Carregando faturas…</p>
      ) : items.length === 0 ? (
        <p className="text-sm text-gray-500 dark:text-gray-400">Nenhuma cobrança encontrada.</p>
      ) : (
        <div className="overflow-x-auto">
          <Table>
            <TableHeader className="border-b border-gray-100 dark:border-white/[0.05]">
              <TableRow>
                <TableCell isHeader className="px-4 py-3 text-start text-theme-xs font-medium text-gray-500 dark:text-gray-400">Data</TableCell>
                <TableCell isHeader className="px-4 py-3 text-start text-theme-xs font-medium text-gray-500 dark:text-gray-400">Valor</TableCell>
                <TableCell isHeader className="px-4 py-3 text-start text-theme-xs font-medium text-gray-500 dark:text-gray-400">Método</TableCell>
                <TableCell isHeader className="px-4 py-3 text-start text-theme-xs font-medium text-gray-500 dark:text-gray-400">Status</TableCell>
                <TableCell isHeader className="px-4 py-3 text-start text-theme-xs font-medium text-gray-500 dark:text-gray-400">Ações</TableCell>
              </TableRow>
            </TableHeader>
            <TableBody className="divide-y divide-gray-100 dark:divide-white/[0.05]">
              {items.map((row, idx) => (
                <TableRow key={`${row.due_date}-${idx}`}>
                  <TableCell className="px-4 py-3 text-theme-sm text-gray-800 dark:text-white/90">{formatDateBR(row.due_date)}</TableCell>
                  <TableCell className="px-4 py-3 text-theme-sm text-gray-500">{formatCurrencyBRL(row.value)}</TableCell>
                  <TableCell className="px-4 py-3 text-theme-sm text-gray-500">{billingTypeLabel(row.billing_type)}</TableCell>
                  <TableCell className="px-4 py-3"><InvoiceStatusBadge status={row.status} /></TableCell>
                  <TableCell className="px-4 py-3">
                    {row.invoice_url ? (
                      <a href={row.invoice_url} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1 text-brand-500 text-theme-sm">
                        <DownloadIcon className="size-5" /> PDF
                      </a>
                    ) : <span className="text-gray-400">—</span>}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}
    </FormSection>
  );
}

import { PencilIcon, TrashBinIcon } from "../../icons";
import { formatMarketAddressDisplay } from "../../features/markets/addressFormat";
import type { Market } from "../../features/markets/types";
import { Table, TableBody, TableCell, TableHeader, TableRow } from "../ui/table";
import MarketStatusBadge from "./MarketStatusBadge";

type Props = {
  markets: Market[];
  loading: boolean;
  filtersActive?: boolean;
  onEdit: (market: Market) => void;
  onDelete: (market: Market) => void;
};

function SkeletonRows() {
  return (
    <>
      {[1, 2, 3].map((row) => (
        <TableRow key={row}>
          {[1, 2, 3, 4].map((col) => (
            <TableCell key={col} className="px-4 py-3">
              <div className="h-4 w-full max-w-[12rem] animate-pulse rounded bg-gray-100 dark:bg-white/10" />
            </TableCell>
          ))}
        </TableRow>
      ))}
    </>
  );
}

export default function MarketsTable({ markets, loading, filtersActive = false, onEdit, onDelete }: Props) {
  if (!loading && markets.length === 0) {
    return (
      <p className="text-sm text-gray-500 dark:text-gray-400">
        {filtersActive
          ? "Nenhum mercado encontrado com os filtros informados."
          : 'Nenhum mercado cadastrado. Clique em "Adicionar Novo Mercado" para começar.'}
      </p>
    );
  }

  return (
    <div className="overflow-x-auto">
      <Table>
        <TableHeader className="border-b border-gray-100 dark:border-white/[0.05]">
          <TableRow>
            <TableCell isHeader className="px-4 py-3 text-start text-theme-xs font-medium text-gray-500 dark:text-gray-400">
              Nome do Condomínio
            </TableCell>
            <TableCell isHeader className="px-4 py-3 text-start text-theme-xs font-medium text-gray-500 dark:text-gray-400">
              Endereço
            </TableCell>
            <TableCell isHeader className="px-4 py-3 text-start text-theme-xs font-medium text-gray-500 dark:text-gray-400">
              Status
            </TableCell>
            <TableCell isHeader className="px-4 py-3 text-start text-theme-xs font-medium text-gray-500 dark:text-gray-400">
              Ações
            </TableCell>
          </TableRow>
        </TableHeader>
        <TableBody className="divide-y divide-gray-100 dark:divide-white/[0.05]">
          {loading ? (
            <SkeletonRows />
          ) : (
            markets.map((market) => (
              <TableRow key={market.id}>
                <TableCell className="px-4 py-3 text-theme-sm font-medium text-gray-800 dark:text-white/90">
                  {market.name}
                </TableCell>
                <TableCell className="max-w-xs px-4 py-3 text-theme-sm text-gray-600 dark:text-gray-300">
                  {formatMarketAddressDisplay(market.address)}
                </TableCell>
                <TableCell className="px-4 py-3">
                  <MarketStatusBadge status={market.status} />
                </TableCell>
                <TableCell className="px-4 py-3">
                  <div className="flex items-center gap-2">
                    <button
                      type="button"
                      onClick={() => onEdit(market)}
                      className="inline-flex h-9 w-9 items-center justify-center rounded-lg border border-gray-200 text-gray-600 hover:bg-gray-50 dark:border-gray-700 dark:text-gray-300 dark:hover:bg-white/5"
                      aria-label={`Editar ${market.name}`}
                    >
                      <PencilIcon className="size-4" />
                    </button>
                    <button
                      type="button"
                      onClick={() => onDelete(market)}
                      className="inline-flex h-9 w-9 items-center justify-center rounded-lg border border-gray-200 text-error-500 hover:bg-error-50 dark:border-gray-700 dark:hover:bg-error-500/10"
                      aria-label={`Excluir ${market.name}`}
                    >
                      <TrashBinIcon className="size-4" />
                    </button>
                  </div>
                </TableCell>
              </TableRow>
            ))
          )}
        </TableBody>
      </Table>
    </div>
  );
}

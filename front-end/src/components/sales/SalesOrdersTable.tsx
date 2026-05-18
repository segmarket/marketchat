import { Eye } from "lucide-react";
import { formatBRL, formatOrderDateTime } from "../../features/sales/format";
import type { SalesOrderRow } from "../../features/sales/types";
import { Table, TableBody, TableCell, TableHeader, TableRow } from "../ui/table";
import Button from "../ui/button/Button";
import CartStatusBadge from "./CartStatusBadge";

type Props = {
  rows: SalesOrderRow[];
  loading: boolean;
  filtersActive?: boolean;
  onViewDetail: (row: SalesOrderRow) => void;
};

function SkeletonRows() {
  return (
    <>
      {[1, 2, 3].map((row) => (
        <TableRow key={row}>
          {[1, 2, 3, 4, 5, 6].map((col) => (
            <TableCell key={col} className="px-4 py-3">
              <div className="h-4 w-full max-w-[10rem] animate-pulse rounded bg-gray-100 dark:bg-white/10" />
            </TableCell>
          ))}
        </TableRow>
      ))}
    </>
  );
}

export default function SalesOrdersTable({
  rows,
  loading,
  filtersActive = false,
  onViewDetail,
}: Props) {
  if (!loading && rows.length === 0) {
    return (
      <p className="text-sm text-gray-500 dark:text-gray-400">
        {filtersActive
          ? "Nenhum pedido encontrado com os filtros informados."
          : "Nenhum pedido registrado ainda."}
      </p>
    );
  }

  return (
    <div className="overflow-x-auto">
      <Table>
        <TableHeader className="border-b border-gray-100 dark:border-white/[0.05]">
          <TableRow>
            <TableCell isHeader className="px-4 py-3 text-start text-theme-xs font-medium text-gray-500">
              Cód. pedido
            </TableCell>
            <TableCell isHeader className="px-4 py-3 text-start text-theme-xs font-medium text-gray-500">
              Morador
            </TableCell>
            <TableCell isHeader className="px-4 py-3 text-start text-theme-xs font-medium text-gray-500">
              Condomínio
            </TableCell>
            <TableCell isHeader className="px-4 py-3 text-start text-theme-xs font-medium text-gray-500">
              Data/hora
            </TableCell>
            <TableCell isHeader className="px-4 py-3 text-start text-theme-xs font-medium text-gray-500">
              Valor total
            </TableCell>
            <TableCell isHeader className="px-4 py-3 text-start text-theme-xs font-medium text-gray-500">
              Status
            </TableCell>
            <TableCell isHeader className="px-4 py-3 text-start text-theme-xs font-medium text-gray-500">
              Ações
            </TableCell>
          </TableRow>
        </TableHeader>
        <TableBody className="divide-y divide-gray-100 dark:divide-white/[0.05]">
          {loading ? (
            <SkeletonRows />
          ) : (
            rows.map((row) => (
              <TableRow key={row.id}>
                <TableCell className="px-4 py-3 text-theme-sm font-medium text-gray-800">
                  #{row.id}
                </TableCell>
                <TableCell className="px-4 py-3 text-theme-sm text-gray-800 dark:text-white/90">
                  {row.resident_name || "—"}
                </TableCell>
                <TableCell className="px-4 py-3">
                  {row.market_name ? (
                    <span className="inline-flex rounded-md bg-gray-100 px-2 py-0.5 text-xs font-medium text-gray-700">
                      {row.market_name}
                    </span>
                  ) : (
                    <span className="text-theme-sm text-gray-400">—</span>
                  )}
                </TableCell>
                <TableCell className="px-4 py-3 text-theme-sm text-gray-600">
                  {formatOrderDateTime(row.created_at)}
                </TableCell>
                <TableCell className="px-4 py-3 text-theme-sm font-medium text-gray-800">
                  {formatBRL(row.total_value)}
                </TableCell>
                <TableCell className="px-4 py-3">
                  <CartStatusBadge status={row.status} />
                </TableCell>
                <TableCell className="px-4 py-3">
                  <Button
                    type="button"
                    size="sm"
                    variant="outline"
                    startIcon={<Eye className="size-4" />}
                    onClick={() => onViewDetail(row)}
                  >
                    Ver pedido
                  </Button>
                </TableCell>
              </TableRow>
            ))
          )}
        </TableBody>
      </Table>
    </div>
  );
}

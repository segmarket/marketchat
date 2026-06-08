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

const mobileCardClassName =
  "mb-3 rounded-xl border border-gray-200 bg-white p-4 dark:border-gray-800 dark:bg-white/[0.03]";

function SkeletonTableRows() {
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

function SkeletonMobileCards() {
  return (
    <div className="space-y-3 md:hidden">
      {[1, 2, 3].map((i) => (
        <div
          key={i}
          className="h-36 animate-pulse rounded-xl border border-gray-200 bg-gray-50 dark:border-gray-800 dark:bg-white/5"
        />
      ))}
    </div>
  );
}

function OrderMobileCard({
  row,
  onViewDetail,
}: {
  row: SalesOrderRow;
  onViewDetail: (row: SalesOrderRow) => void;
}) {
  return (
    <div className={mobileCardClassName}>
      <div className="flex items-start justify-between gap-2">
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-sm font-semibold text-gray-800 dark:text-white/90">#{row.id}</span>
          <CartStatusBadge status={row.status} />
        </div>
        <span className="shrink-0 text-xs text-gray-500 dark:text-gray-400">
          {formatOrderDateTime(row.created_at)}
        </span>
      </div>
      <p className="mt-3 font-semibold text-gray-800 dark:text-white/90">
        {row.resident_name || "—"}
      </p>
      {row.market_name ? (
        <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">{row.market_name}</p>
      ) : null}
      <p className="mt-3 text-lg font-bold text-gray-800 dark:text-white/90">
        {formatBRL(row.total_value)}
      </p>
      <Button
        type="button"
        size="sm"
        variant="outline"
        className="mt-3 min-h-[44px] w-full"
        startIcon={<Eye className="size-4" />}
        onClick={() => onViewDetail(row)}
      >
        Ver pedido
      </Button>
    </div>
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

  if (loading) {
    return (
      <>
        <div className="hidden overflow-x-auto md:block">
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
            <TableBody>
              <SkeletonTableRows />
            </TableBody>
          </Table>
        </div>
        <SkeletonMobileCards />
      </>
    );
  }

  return (
    <>
      <div className="hidden overflow-x-auto md:block">
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
            {rows.map((row) => (
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
            ))}
          </TableBody>
        </Table>
      </div>

      <div className="block md:hidden">
        {rows.map((row) => (
          <OrderMobileCard key={row.id} row={row} onViewDetail={onViewDetail} />
        ))}
      </div>
    </>
  );
}

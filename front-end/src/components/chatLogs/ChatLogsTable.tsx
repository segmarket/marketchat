import { formatAttendanceDateTime } from "../../features/chatLogs/format";
import { formatPhoneBR } from "../../features/residents/format";
import type { ChatAttendanceRow } from "../../features/chatLogs/types";
import { Table, TableBody, TableCell, TableHeader, TableRow } from "../ui/table";
import IntentTypeBadge from "./IntentTypeBadge";
import Button from "../ui/button/Button";

type Props = {
  rows: ChatAttendanceRow[];
  loading: boolean;
  filtersActive?: boolean;
  onViewConversation: (row: ChatAttendanceRow) => void;
};

function SkeletonRows() {
  return (
    <>
      {[1, 2, 3].map((row) => (
        <TableRow key={row}>
          {[1, 2, 3, 4, 5].map((col) => (
            <TableCell key={col} className="px-4 py-3">
              <div className="h-4 w-full max-w-[10rem] animate-pulse rounded bg-gray-100 dark:bg-white/10" />
            </TableCell>
          ))}
        </TableRow>
      ))}
    </>
  );
}

export default function ChatLogsTable({
  rows,
  loading,
  filtersActive = false,
  onViewConversation,
}: Props) {
  if (!loading && rows.length === 0) {
    return (
      <p className="text-sm text-gray-500 dark:text-gray-400">
        {filtersActive
          ? "Nenhum atendimento encontrado com os filtros informados."
          : "Nenhum atendimento registrado ainda."}
      </p>
    );
  }

  return (
    <div className="overflow-x-auto">
      <Table>
        <TableHeader className="border-b border-gray-100 dark:border-white/[0.05]">
          <TableRow>
            <TableCell isHeader className="px-4 py-3 text-start text-theme-xs font-medium text-gray-500">
              Morador
            </TableCell>
            <TableCell isHeader className="px-4 py-3 text-start text-theme-xs font-medium text-gray-500">
              Condomínio
            </TableCell>
            <TableCell isHeader className="px-4 py-3 text-start text-theme-xs font-medium text-gray-500">
              Tipo
            </TableCell>
            <TableCell isHeader className="px-4 py-3 text-start text-theme-xs font-medium text-gray-500">
              Horário
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
              <TableRow key={`${row.session_id}-${row.attendance_date}`}>
                <TableCell className="px-4 py-3">
                  <p className="text-theme-sm font-semibold text-gray-800 dark:text-white/90">
                    {row.resident_name || "—"}
                  </p>
                  <p className="text-xs text-gray-500">
                    {row.resident_phone ? formatPhoneBR(row.resident_phone) : "—"}
                  </p>
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
                <TableCell className="px-4 py-3">
                  <IntentTypeBadge intentType={row.intent_type} />
                </TableCell>
                <TableCell className="px-4 py-3 text-theme-sm text-gray-600 dark:text-gray-300">
                  {formatAttendanceDateTime(row.last_at)}
                </TableCell>
                <TableCell className="px-4 py-3">
                  <Button
                    type="button"
                    size="sm"
                    variant="outline"
                    onClick={() => onViewConversation(row)}
                  >
                    Ver conversa
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

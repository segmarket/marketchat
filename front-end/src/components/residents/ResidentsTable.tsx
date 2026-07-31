import { PencilIcon, TrashBinIcon } from "../../icons";
import { formatDateBR, formatPhoneBR } from "../../features/residents/format";
import type { Resident } from "../../features/residents/types";
import { Table, TableBody, TableCell, TableHeader, TableRow } from "../ui/table";

type Props = {
  residents: Resident[];
  loading: boolean;
  filtersActive?: boolean;
  canDelete?: boolean;
  onEdit: (resident: Resident) => void;
  onDelete?: (resident: Resident) => void;
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

export default function ResidentsTable({
  residents,
  loading,
  filtersActive = false,
  canDelete = false,
  onEdit,
  onDelete,
}: Props) {
  if (!loading && residents.length === 0) {
    return (
      <p className="text-sm text-gray-500 dark:text-gray-400">
        {filtersActive
          ? "Nenhum morador encontrado com os filtros informados."
          : "Nenhum morador cadastrado via WhatsApp ainda."}
      </p>
    );
  }

  return (
    <div className="overflow-x-auto">
      <Table>
        <TableHeader className="border-b border-gray-100 dark:border-white/[0.05]">
          <TableRow>
            <TableCell isHeader className="px-4 py-3 text-start text-theme-xs font-medium text-gray-500 dark:text-gray-400">
              Nome do Morador
            </TableCell>
            <TableCell isHeader className="px-4 py-3 text-start text-theme-xs font-medium text-gray-500 dark:text-gray-400">
              WhatsApp
            </TableCell>
            <TableCell isHeader className="px-4 py-3 text-start text-theme-xs font-medium text-gray-500 dark:text-gray-400">
              Condomínio / Mercado
            </TableCell>
            <TableCell isHeader className="px-4 py-3 text-start text-theme-xs font-medium text-gray-500 dark:text-gray-400">
              Data de Cadastro
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
            residents.map((resident) => (
              <TableRow key={resident.id}>
                <TableCell className="px-4 py-3 text-theme-sm font-medium text-gray-800 dark:text-white/90">
                  {resident.name}
                </TableCell>
                <TableCell className="px-4 py-3 text-theme-sm text-gray-600 dark:text-gray-300">
                  {formatPhoneBR(resident.phone_number)}
                </TableCell>
                <TableCell className="px-4 py-3 text-theme-sm text-gray-600 dark:text-gray-300">
                  {resident.market?.name ?? "—"}
                </TableCell>
                <TableCell className="px-4 py-3 text-theme-sm text-gray-600 dark:text-gray-300">
                  {formatDateBR(resident.created_at)}
                </TableCell>
                <TableCell className="px-4 py-3">
                  <div className="flex items-center gap-2">
                    <button
                      type="button"
                      onClick={() => onEdit(resident)}
                      className="inline-flex h-9 w-9 items-center justify-center rounded-lg border border-gray-200 text-gray-600 hover:bg-gray-50 dark:border-gray-700 dark:text-gray-300 dark:hover:bg-white/5"
                      aria-label={`Editar ${resident.name}`}
                    >
                      <PencilIcon className="size-4" />
                    </button>
                    {canDelete && onDelete ? (
                      <button
                        type="button"
                        onClick={() => onDelete(resident)}
                        className="inline-flex h-9 w-9 items-center justify-center rounded-lg border border-error-200 text-error-600 hover:bg-error-50 dark:border-error-500/40 dark:text-error-400 dark:hover:bg-error-500/10"
                        aria-label={`Excluir ${resident.name}`}
                      >
                        <TrashBinIcon className="size-4" />
                      </button>
                    ) : null}
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

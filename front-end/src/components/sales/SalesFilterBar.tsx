import { useEffect, useId, useRef } from "react";
import { Search } from "lucide-react";
import flatpickr from "flatpickr";
import Button from "../ui/button/Button";
import Label from "../form/Label";
import { STATUS_OPTIONS } from "../../features/sales/format";
import type { SalesMarketOption } from "../../features/sales/types";
import type { SalesSearchFilters } from "../../features/sales/searchTypes";

const selectClassName =
  "h-11 w-full rounded-lg border border-gray-300 bg-white px-4 py-2.5 text-sm shadow-sm focus:border-brand-300 focus:outline-hidden focus:ring-3 focus:ring-brand-500/20 dark:border-gray-700 dark:bg-gray-900 dark:text-white/90";

const inputClassName =
  "h-11 w-full rounded-lg border border-gray-300 bg-white pl-10 pr-4 py-2.5 text-sm shadow-sm focus:border-brand-300 focus:outline-hidden focus:ring-3 focus:ring-brand-500/20 dark:border-gray-700 dark:bg-gray-900 dark:text-white/90";

type Props = {
  filters: SalesSearchFilters;
  markets: SalesMarketOption[];
  busy?: boolean;
  onChange: (filters: SalesSearchFilters) => void;
  onClear: () => void;
};

export default function SalesFilterBar({
  filters,
  markets,
  busy = false,
  onChange,
  onClear,
}: Props) {
  const dateInputId = useId();
  const dateRef = useRef<HTMLInputElement | null>(null);
  const onChangeRef = useRef(onChange);
  const filtersRef = useRef(filters);

  onChangeRef.current = onChange;
  filtersRef.current = filters;

  useEffect(() => {
    if (!dateRef.current) return;
    const fp = flatpickr(dateRef.current, {
      mode: "range",
      dateFormat: "Y-m-d",
      static: true,
      onChange: (selectedDates) => {
        const current = filtersRef.current;
        if (selectedDates.length === 0) {
          onChangeRef.current({ ...current, dateFrom: "", dateTo: "" });
          return;
        }
        const from = selectedDates[0];
        const to = selectedDates[1] ?? selectedDates[0];
        const fmt = (d: Date) => {
          const y = d.getFullYear();
          const m = String(d.getMonth() + 1).padStart(2, "0");
          const day = String(d.getDate()).padStart(2, "0");
          return `${y}-${m}-${day}`;
        };
        onChangeRef.current({
          ...current,
          dateFrom: fmt(from),
          dateTo: fmt(to),
        });
      },
    });
    return () => {
      if (!Array.isArray(fp)) fp.destroy();
    };
  }, []);

  function patch(partial: Partial<SalesSearchFilters>) {
    onChange({ ...filters, ...partial });
  }

  return (
    <div className="mb-6 rounded-md border border-gray-200 bg-white p-4 shadow-sm dark:border-gray-800 dark:bg-white/[0.03]">
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-5">
        <div className="space-y-1.5">
          <Label htmlFor="sales-filter-name">Nome do morador</Label>
          <div className="relative">
            <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-gray-400" />
            <input
              id="sales-filter-name"
              type="text"
              value={filters.residentName}
              onChange={(e) => patch({ residentName: e.target.value })}
              placeholder="Buscar por nome"
              className={inputClassName}
              disabled={busy}
            />
          </div>
        </div>

        <div className="space-y-1.5">
          <Label htmlFor="sales-filter-market">Condomínio</Label>
          <select
            id="sales-filter-market"
            value={filters.marketId}
            onChange={(e) => patch({ marketId: e.target.value })}
            className={selectClassName}
            disabled={busy}
          >
            <option value="">Todos os condomínios</option>
            {markets.map((m) => (
              <option key={m.id} value={String(m.id)}>
                {m.name}
              </option>
            ))}
          </select>
        </div>

        <div className="space-y-1.5">
          <Label htmlFor="sales-filter-status">Status da venda</Label>
          <select
            id="sales-filter-status"
            value={filters.status}
            onChange={(e) =>
              patch({ status: e.target.value as SalesSearchFilters["status"] })
            }
            className={selectClassName}
            disabled={busy}
          >
            {STATUS_OPTIONS.map((opt) => (
              <option key={opt.value || "all"} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </div>

        <div className="space-y-1.5 lg:col-span-2">
          <Label htmlFor={dateInputId}>Período</Label>
          <input
            ref={dateRef}
            id={dateInputId}
            type="text"
            placeholder="Data inicial — Data final"
            className={inputClassName.replace("pl-10", "px-4")}
            disabled={busy}
          />
        </div>
      </div>

      <div className="mt-4 flex justify-end">
        <Button type="button" variant="outline" size="sm" onClick={onClear} disabled={busy}>
          Limpar filtros
        </Button>
      </div>
    </div>
  );
}

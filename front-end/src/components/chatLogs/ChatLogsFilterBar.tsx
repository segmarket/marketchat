import { Search } from "lucide-react";
import { IMaskInput } from "react-imask";
import DatePicker from "../form/date-picker";
import Button from "../ui/button/Button";
import Label from "../form/Label";
import { INTENT_OPTIONS } from "../../features/chatLogs/format";
import { maskPhoneInput } from "../../features/residents/format";
import type { ChatLogsMarketOption } from "../../features/chatLogs/types";
import type { ChatLogsSearchFilters } from "../../features/chatLogs/searchTypes";

const selectClassName =
  "h-11 w-full rounded-lg border border-gray-300 bg-white px-4 py-2.5 text-sm shadow-sm focus:border-brand-300 focus:outline-hidden focus:ring-3 focus:ring-brand-500/20 dark:border-gray-700 dark:bg-gray-900 dark:text-white/90";

const inputClassName =
  "h-11 w-full rounded-lg border border-gray-300 bg-white pl-10 pr-4 py-2.5 text-sm shadow-sm focus:border-brand-300 focus:outline-hidden focus:ring-3 focus:ring-brand-500/20 dark:border-gray-700 dark:bg-gray-900 dark:text-white/90";

type Props = {
  filters: ChatLogsSearchFilters;
  markets: ChatLogsMarketOption[];
  busy?: boolean;
  onChange: (filters: ChatLogsSearchFilters) => void;
  onClear: () => void;
};

export default function ChatLogsFilterBar({
  filters,
  markets,
  busy = false,
  onChange,
  onClear,
}: Props) {
  function patch(partial: Partial<ChatLogsSearchFilters>) {
    onChange({ ...filters, ...partial });
  }

  return (
    <div className="mb-6 rounded-md border border-gray-200 bg-white p-4 shadow-sm dark:border-gray-800 dark:bg-white/[0.03]">
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-5">
        <div className="space-y-1.5">
          <Label htmlFor="chat-logs-name">Nome do morador</Label>
          <div className="relative">
            <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-gray-400" />
            <input
              id="chat-logs-name"
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
          <Label htmlFor="chat-logs-phone">Telefone</Label>
          <IMaskInput
            id="chat-logs-phone"
            mask={[
              { mask: "(00) 00000-0000" },
              { mask: "(00) 0000-0000" },
            ]}
            value={filters.phone}
            onAccept={(value: string) => patch({ phone: maskPhoneInput(String(value)) })}
            placeholder="(11) 99999-9999"
            className={inputClassName.replace("pl-10", "px-4")}
            disabled={busy}
          />
        </div>

        <div className="space-y-1.5">
          <Label htmlFor="chat-logs-market">Condomínio</Label>
          <select
            id="chat-logs-market"
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
          <Label htmlFor="chat-logs-intent">Tipo de atendimento</Label>
          <select
            id="chat-logs-intent"
            value={filters.intentType}
            onChange={(e) =>
              patch({ intentType: e.target.value as ChatLogsSearchFilters["intentType"] })
            }
            className={selectClassName}
            disabled={busy}
          >
            {INTENT_OPTIONS.map((opt) => (
              <option key={opt.value || "all"} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </div>

        <div className="space-y-1.5">
          <DatePicker
            id="chat-logs-date"
            label="Data do atendimento"
            placeholder="Selecione o dia"
            defaultDate={filters.date || undefined}
            onChange={(_dates, dateStr) => {
              patch({ date: dateStr });
            }}
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

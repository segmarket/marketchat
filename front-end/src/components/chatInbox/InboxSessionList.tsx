import { formatAttendanceDateTime } from "../../features/chatLogs/format";
import { hasUnreadInbound } from "../../features/chatLogs/inboxUnread";
import type { InboxSessionRow } from "../../features/chatLogs/types";
import { formatPhoneBR } from "../../features/residents/format";

type Props = {
  rows: InboxSessionRow[];
  loading: boolean;
  selectedSessionId: number | null;
  onSelect: (row: InboxSessionRow) => void;
  /** Incrementado ao marcar lido / poll para reavaliar badges. */
  unreadTick?: number;
};

function formatListTime(iso: string): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return "";
  const now = new Date();
  const sameDay =
    date.getFullYear() === now.getFullYear()
    && date.getMonth() === now.getMonth()
    && date.getDate() === now.getDate();
  if (sameDay) {
    return new Intl.DateTimeFormat("pt-BR", {
      hour: "2-digit",
      minute: "2-digit",
    }).format(date);
  }
  return formatAttendanceDateTime(iso);
}

export default function InboxSessionList({
  rows,
  loading,
  selectedSessionId,
  onSelect,
  unreadTick = 0,
}: Props) {
  void unreadTick;

  if (loading && rows.length === 0) {
    return (
      <div className="flex min-h-0 flex-1 items-center justify-center overflow-y-auto p-6">
        <p className="text-sm text-gray-500">Carregando conversas…</p>
      </div>
    );
  }

  if (!loading && rows.length === 0) {
    return (
      <div className="flex min-h-0 flex-1 items-center justify-center overflow-y-auto p-6">
        <p className="text-center text-sm text-gray-500">
          Nenhuma conversa neste filtro.
        </p>
      </div>
    );
  }

  return (
    <ul className="min-h-0 flex-1 overflow-y-auto">
      {rows.map((row) => {
        const selected = row.session_id === selectedSessionId;
        const unread = hasUnreadInbound(row.session_id, row.last_inbound_id);
        const title = row.resident_name || formatPhoneBR(row.resident_phone) || "Sem nome";

        return (
          <li key={row.session_id}>
            <button
              type="button"
              onClick={() => onSelect(row)}
              className={`flex w-full gap-3 border-b border-gray-100 px-4 py-3 text-left transition-colors dark:border-gray-800/80 ${
                selected
                  ? "bg-brand-50/80 dark:bg-brand-500/10"
                  : "hover:bg-gray-50 dark:hover:bg-white/[0.04]"
              }`}
            >
              <div
                className={`mt-1 size-2.5 shrink-0 rounded-full ${
                  unread ? "bg-brand-500" : "bg-transparent"
                }`}
                aria-hidden
              />
              <div className="min-w-0 flex-1">
                <div className="flex items-baseline justify-between gap-2">
                  <p
                    className={`truncate text-sm ${
                      unread
                        ? "font-semibold text-gray-900 dark:text-white"
                        : "font-medium text-gray-800 dark:text-white/90"
                    }`}
                  >
                    {title}
                  </p>
                  <span className="shrink-0 text-[11px] text-gray-400">
                    {formatListTime(row.last_at)}
                  </span>
                </div>
                <div className="mt-0.5 flex items-center gap-2">
                  <p className="truncate text-xs text-gray-500">
                    {row.preview || "—"}
                  </p>
                  {!row.is_bot_active ? (
                    <span className="shrink-0 rounded bg-amber-100 px-1.5 py-0.5 text-[10px] font-medium text-amber-800 dark:bg-amber-500/20 dark:text-amber-200">
                      Humano
                    </span>
                  ) : null}
                </div>
                {row.market_name ? (
                  <p className="mt-0.5 truncate text-[11px] text-gray-400">
                    {row.market_name}
                  </p>
                ) : null}
              </div>
            </button>
          </li>
        );
      })}
    </ul>
  );
}

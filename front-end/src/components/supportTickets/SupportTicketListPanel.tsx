import {
  formatTicketDate,
  truncateRoute,
} from "../../features/supportTickets/format";
import type { SupportTicketSummary } from "../../features/supportTickets/types";
import SupportTicketStatusBadge from "./SupportTicketStatusBadge";

type Props = {
  tickets: SupportTicketSummary[];
  selectedId: number | null;
  loading: boolean;
  onSelect: (id: number) => void;
};

export default function SupportTicketListPanel({
  tickets,
  selectedId,
  loading,
  onSelect,
}: Props) {
  if (loading) {
    return <p className="p-4 text-sm text-gray-500">Carregando chamados…</p>;
  }

  if (tickets.length === 0) {
    return (
      <p className="p-6 text-center text-sm text-gray-500 dark:text-gray-400">
        Nenhum chamado registrado ainda.
      </p>
    );
  }

  return (
    <ul className="divide-y divide-gray-100 dark:divide-gray-800">
      {tickets.map((ticket) => {
        const active = ticket.id === selectedId;
        return (
          <li key={ticket.id}>
            <button
              type="button"
              onClick={() => onSelect(ticket.id)}
              className={`w-full px-4 py-3 text-left transition hover:bg-gray-50 dark:hover:bg-white/[0.03] ${
                active ? "bg-brand-50/80 dark:bg-brand-500/10" : ""
              }`}
            >
              <div className="flex items-start justify-between gap-2">
                <span className="line-clamp-2 text-sm font-medium text-gray-900 dark:text-white/90">
                  {ticket.subject}
                </span>
                <SupportTicketStatusBadge status={ticket.status} />
              </div>
              <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
                {formatTicketDate(ticket.created_at)}
              </p>
              <p className="mt-0.5 truncate text-xs text-gray-400" title={ticket.category_route}>
                {truncateRoute(ticket.category_route)}
              </p>
              <p className="mt-1 text-xs text-gray-400">{ticket.user_email}</p>
            </button>
          </li>
        );
      })}
    </ul>
  );
}

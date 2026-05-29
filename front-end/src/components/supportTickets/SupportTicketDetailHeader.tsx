import { ArrowLeft, Check } from "lucide-react";
import { ticketStatusLabel } from "../../features/supportTickets/format";
import type { SupportTicketDetail } from "../../features/supportTickets/types";
import SupportTicketCloseButton from "./SupportTicketCloseButton";
import SupportTicketStatusBadge from "./SupportTicketStatusBadge";

type Props = {
  ticket: SupportTicketDetail;
  resolving: boolean;
  onBack: () => void;
  onClose: () => void;
  onResolve: () => void;
};

export default function SupportTicketDetailHeader({
  ticket,
  resolving,
  onBack,
  onClose,
  onResolve,
}: Props) {
  const canResolve = ticket.status === "NEW" || ticket.status === "IN_PROGRESS";

  return (
    <header className="flex shrink-0 items-start justify-between gap-3 border-b border-gray-200 p-4 dark:border-gray-800">
      <div className="flex min-w-0 flex-1 items-start gap-2">
        <button
          type="button"
          onClick={onBack}
          aria-label="Voltar para a lista"
          className="mt-0.5 shrink-0 rounded-lg p-1.5 text-gray-600 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-white/10"
        >
          <ArrowLeft className="size-5" />
        </button>
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <h2 className="truncate text-base font-semibold text-gray-900 dark:text-white/90">
              {ticket.subject}
            </h2>
            <SupportTicketStatusBadge status={ticket.status} />
          </div>
          <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
            {ticket.user_email}
          </p>
        </div>
      </div>

      <div className="flex shrink-0 flex-wrap items-center justify-end gap-2">
        {canResolve ? (
          <button
            type="button"
            onClick={onResolve}
            disabled={resolving}
            className="inline-flex items-center gap-1.5 rounded-lg border border-gray-200 px-3 py-1.5 text-xs font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50 dark:border-gray-700 dark:text-gray-300 dark:hover:bg-white/5"
          >
            <Check className="size-4" />
            {resolving ? "Salvando…" : "Marcar como resolvido"}
          </button>
        ) : (
          <span className="text-xs text-gray-400">{ticketStatusLabel(ticket.status)}</span>
        )}
        <SupportTicketCloseButton onClick={onClose} />
      </div>
    </header>
  );
}

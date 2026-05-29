import { ticketStatusBadgeClass, ticketStatusLabel } from "../../features/supportTickets/format";

type Props = {
  status: string;
};

export default function SupportTicketStatusBadge({ status }: Props) {
  return (
    <span
      className={`inline-flex shrink-0 items-center rounded-md px-2 py-0.5 text-xs font-medium ring-1 ring-inset ${ticketStatusBadgeClass(status)}`}
    >
      {ticketStatusLabel(status)}
    </span>
  );
}

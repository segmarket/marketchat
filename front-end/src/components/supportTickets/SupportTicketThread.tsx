import { formatTicketDate } from "../../features/supportTickets/format";
import type { SupportTicketDetail } from "../../features/supportTickets/types";

type Props = {
  ticket: SupportTicketDetail;
};

export default function SupportTicketThread({ ticket }: Props) {
  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <p
        className="shrink-0 border-b border-gray-100 px-5 py-2 text-xs text-gray-400 dark:border-gray-800"
        title={ticket.category_route}
      >
        Tela: {ticket.category_route} · Aberto em {formatTicketDate(ticket.created_at)}
      </p>

      <div className="flex min-h-0 flex-1 flex-col gap-3 overflow-y-auto px-5 py-4">
        {ticket.messages.map((msg) => {
          const fromSupport = msg.is_from_admin;
          return (
            <div
              key={msg.id}
              className={`flex ${fromSupport ? "justify-start" : "justify-end"}`}
            >
              <div
                className={`max-w-[90%] rounded-2xl px-3 py-2 text-sm leading-relaxed whitespace-pre-wrap ${
                  fromSupport
                    ? "rounded-bl-sm border border-gray-200/80 bg-gray-50 text-gray-800 dark:border-gray-700 dark:bg-gray-800/80 dark:text-gray-100"
                    : "rounded-br-sm bg-brand-500 text-white"
                }`}
              >
                <p
                  className={`mb-1 text-xs font-medium ${
                    fromSupport ? "text-gray-500 dark:text-gray-400" : "text-white/80"
                  }`}
                >
                  {fromSupport ? "Suporte Marketchat" : msg.sender_name || msg.sender_email}
                  {" · "}
                  {formatTicketDate(msg.created_at)}
                </p>
                {msg.message}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

import { useEffect } from "react";
import { X } from "lucide-react";
import {
  formatAttendanceDateOnly,
  formatAttendanceDateTime,
} from "../../features/chatLogs/format";
import { formatPhoneBR } from "../../features/residents/format";
import type { ChatConversationResponse } from "../../features/chatLogs/types";

type Props = {
  open: boolean;
  loading: boolean;
  conversation: ChatConversationResponse | null;
  onClose: () => void;
};

export default function ChatConversationDrawer({
  open,
  loading,
  conversation,
  onClose,
}: Props) {
  useEffect(() => {
    if (!open) return;
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-[99999] flex justify-end">
      <button
        type="button"
        aria-label="Fechar conversa"
        className="absolute inset-0 bg-black/40"
        onClick={onClose}
      />
      <aside className="relative flex h-full w-full max-w-md translate-x-0 flex-col bg-white shadow-xl transition-transform duration-300 dark:bg-gray-900">
        <header className="flex items-start justify-between border-b border-gray-200 px-5 py-4 dark:border-gray-800">
          <div>
            <h2 className="text-lg font-semibold text-gray-800 dark:text-white/90">
              {conversation?.resident_name || "Atendimento"}
            </h2>
            <p className="text-sm text-gray-500">
              {conversation?.market_name || "—"}
              {conversation?.attendance_date
                ? ` · ${formatAttendanceDateOnly(conversation.attendance_date)}`
                : ""}
            </p>
            {conversation?.resident_phone ? (
              <p className="mt-1 text-xs text-gray-400">
                {formatPhoneBR(conversation.resident_phone)}
              </p>
            ) : null}
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg p-1 text-gray-500 hover:bg-gray-100 dark:hover:bg-white/10"
          >
            <X className="size-5" />
          </button>
        </header>

        <div className="flex-1 space-y-3 overflow-y-auto bg-gray-50 px-4 py-4 dark:bg-gray-950">
          {loading ? (
            <p className="text-sm text-gray-500">Carregando mensagens…</p>
          ) : (
            conversation?.messages.map((msg) => {
              const inbound = msg.direction === "INBOUND";
              return (
                <div
                  key={msg.id}
                  className={`flex ${inbound ? "justify-end" : "justify-start"}`}
                >
                  <div
                    className={`max-w-[85%] rounded-2xl px-3 py-2 text-sm shadow-sm ${
                      inbound
                        ? "rounded-br-sm bg-emerald-100 text-emerald-950"
                        : "rounded-bl-sm bg-gray-200 text-gray-800 dark:bg-gray-800 dark:text-gray-100"
                    }`}
                  >
                    {msg.message_kind === "image" && msg.attachment_url ? (
                      <img
                        src={msg.attachment_url}
                        alt="Anexo"
                        className="mb-2 max-h-48 w-full rounded-lg object-cover"
                      />
                    ) : null}
                    {msg.message_text ? (
                      <p className="whitespace-pre-wrap break-words">{msg.message_text}</p>
                    ) : null}
                    <p className="mt-1 text-[10px] opacity-70">
                      {formatAttendanceDateTime(msg.created_at)}
                    </p>
                  </div>
                </div>
              );
            })
          )}
          {!loading && conversation && conversation.messages.length === 0 ? (
            <p className="text-sm text-gray-500">Nenhuma mensagem neste atendimento.</p>
          ) : null}
        </div>
      </aside>
    </div>
  );
}

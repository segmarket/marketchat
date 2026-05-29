import { useCallback, useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { Sparkles } from "lucide-react";
import { useLocation } from "react-router";
import { toast } from "sonner";
import { postSupportChat, postSupportTicket } from "../../features/supportCopilot/api";
import {
  buildTicketDescriptionPrefill,
  suggestTicketSubject,
} from "../../features/supportCopilot/formatChatTranscript";
import {
  buildCurrentRoute,
  getQuickSuggestions,
} from "../../features/supportCopilot/suggestions";
import type { CopilotPanelMode, SupportChatMessage } from "../../features/supportCopilot/types";
import { getAxiosErrorMessage } from "../../utils/apiError";
import SupportCopilotFooter from "./SupportCopilotFooter";
import SupportCopilotHeader from "./SupportCopilotHeader";
import SupportCopilotMessages from "./SupportCopilotMessages";
import SupportCopilotTicketForm from "./SupportCopilotTicketForm";

/** Acima do AppHeader (z-99999) e renderizado via portal no body. */
const PANEL_CLASS =
  "fixed top-[4.5rem] right-4 z-[999999] flex h-[calc(100vh-5.5rem)] w-[380px] max-w-[calc(100vw-2rem)] flex-col overflow-hidden rounded-2xl border border-gray-200 bg-white shadow-2xl transition-[transform,opacity] duration-300 dark:border-gray-800 dark:bg-gray-900";

const FAB_CLASS =
  "fixed bottom-6 right-6 z-[999999] flex size-14 items-center justify-center rounded-full bg-gradient-to-br from-brand-500 to-brand-600 text-white shadow-lg shadow-brand-500/30 transition hover:scale-105 hover:shadow-xl focus:outline-hidden focus:ring-4 focus:ring-brand-500/30";

export default function SupportCopilot() {
  const { pathname, search } = useLocation();
  const [open, setOpen] = useState(false);
  const [mounted, setMounted] = useState(false);
  const [mode, setMode] = useState<CopilotPanelMode>("chat");
  const [messages, setMessages] = useState<SupportChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [ticketSubject, setTicketSubject] = useState("");
  const [ticketDescription, setTicketDescription] = useState("");
  const [ticketSubmitting, setTicketSubmitting] = useState(false);
  const [createdTicketId, setCreatedTicketId] = useState<number | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  const quickSuggestions = getQuickSuggestions(pathname, search);

  const handleClose = useCallback(() => {
    setOpen(false);
  }, []);

  useEffect(() => {
    setMounted(true);
  }, []);

  useEffect(() => {
    if (!open) return;
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") handleClose();
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, handleClose]);

  useEffect(() => {
    if (open && mode === "chat") {
      requestAnimationFrame(() => inputRef.current?.focus());
    }
  }, [open, mode]);

  useEffect(() => {
    const el = scrollRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [messages, loading, open, mode]);

  const openTicketForm = useCallback(() => {
    setTicketSubject(suggestTicketSubject(messages));
    setTicketDescription(buildTicketDescriptionPrefill(messages));
    setMode("ticket");
  }, [messages]);

  const sendMessage = useCallback(
    async (text: string) => {
      const trimmed = text.trim();
      if (!trimmed || loading) return;

      const userMessage: SupportChatMessage = { role: "user", content: trimmed };
      const historyForApi = messages;
      setMessages((prev) => [...prev, userMessage]);
      setInput("");
      setLoading(true);

      try {
        const { reply } = await postSupportChat({
          message: trimmed,
          current_route: buildCurrentRoute(pathname, search),
          chat_history: historyForApi,
        });
        setMessages((prev) => [...prev, { role: "assistant", content: reply }]);
      } catch (err: unknown) {
        setMessages((prev) => prev.slice(0, -1));
        setInput(trimmed);
        toast.error(
          getAxiosErrorMessage(err, {
            notAxiosMessage: "Não foi possível falar com o Suporte Copilot.",
          }),
        );
      } finally {
        setLoading(false);
      }
    },
    [loading, messages, pathname, search],
  );

  const submitTicket = useCallback(async () => {
    const subject = ticketSubject.trim();
    const description = ticketDescription.trim();
    if (!subject || !description || ticketSubmitting) return;

    setTicketSubmitting(true);
    try {
      const ticket = await postSupportTicket({
        subject,
        description,
        category_route: buildCurrentRoute(pathname, search),
      });
      setCreatedTicketId(ticket.id);
      setMode("ticket_sent");
      toast.success("Chamado registrado. Nossa equipe entrará em contato.");
    } catch (err: unknown) {
      toast.error(
        getAxiosErrorMessage(err, {
          notAxiosMessage: "Não foi possível abrir o chamado.",
        }),
      );
    } finally {
      setTicketSubmitting(false);
    }
  }, [ticketSubject, ticketDescription, ticketSubmitting, pathname, search]);

  function handleOpen() {
    setOpen(true);
  }

  function handleBackToChat() {
    setMode("chat");
  }

  if (!mounted) return null;

  return createPortal(
    <>
      <button
        type="button"
        aria-label="Abrir Suporte Copilot"
        onClick={handleOpen}
        className={`${FAB_CLASS} ${open ? "pointer-events-none opacity-0" : "opacity-100"}`}
      >
        <Sparkles className="size-6" strokeWidth={2} />
      </button>

      <aside
        role="dialog"
        aria-modal="true"
        aria-label="Suporte Copilot"
        aria-hidden={!open}
        className={`${PANEL_CLASS} ${
          open
            ? "pointer-events-auto translate-x-0 opacity-100"
            : "pointer-events-none translate-x-[calc(100%+1rem)] opacity-0"
        }`}
      >
        <SupportCopilotHeader
          mode={mode}
          onClose={handleClose}
          onBack={mode === "ticket" ? handleBackToChat : undefined}
        />

        {mode === "chat" ? (
          <>
            <div className="shrink-0 border-b border-gray-100 px-3 py-2 dark:border-gray-800">
              <div className="flex gap-2 overflow-x-auto pb-1">
                {quickSuggestions.map((label) => (
                  <button
                    key={label}
                    type="button"
                    disabled={loading}
                    onClick={() => void sendMessage(label)}
                    className="shrink-0 rounded-full border border-gray-200 bg-gray-50 px-3 py-1.5 text-xs font-medium text-gray-700 hover:border-brand-300 hover:bg-brand-50 hover:text-brand-600 disabled:opacity-50 dark:border-gray-700 dark:bg-gray-800 dark:text-gray-300 dark:hover:border-brand-700 dark:hover:bg-brand-500/10 dark:hover:text-brand-400"
                  >
                    {label}
                  </button>
                ))}
              </div>
            </div>

            <div
              ref={scrollRef}
              className="flex min-h-0 flex-1 flex-col gap-3 overflow-y-auto px-4 py-4"
            >
              <SupportCopilotMessages
                messages={messages}
                loading={loading}
                onOpenTicket={openTicketForm}
              />
            </div>

            <SupportCopilotFooter
              input={input}
              loading={loading}
              inputRef={inputRef}
              onInputChange={setInput}
              onSubmit={() => void sendMessage(input)}
              onOpenTicket={openTicketForm}
            />
          </>
        ) : null}

        {mode === "ticket" ? (
          <SupportCopilotTicketForm
            subject={ticketSubject}
            description={ticketDescription}
            submitting={ticketSubmitting}
            onSubjectChange={setTicketSubject}
            onDescriptionChange={setTicketDescription}
            onSubmit={() => void submitTicket()}
            onCancel={handleBackToChat}
          />
        ) : null}

        {mode === "ticket_sent" ? (
          <div className="flex min-h-0 flex-1 flex-col items-center justify-center gap-4 px-6 py-8 text-center">
            <p className="text-sm text-gray-700 dark:text-gray-300">
              Seu chamado
              {createdTicketId ? ` #${createdTicketId}` : ""} foi registrado. Nossa equipe analisará em
              breve.
            </p>
            <div className="flex w-full flex-col gap-2">
              <button
                type="button"
                onClick={handleBackToChat}
                className="w-full rounded-xl bg-brand-500 px-4 py-2 text-sm font-medium text-white hover:bg-brand-600"
              >
                Voltar ao chat
              </button>
              <button
                type="button"
                onClick={handleClose}
                className="w-full rounded-xl border border-gray-200 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 dark:border-gray-700 dark:text-gray-300 dark:hover:bg-white/5"
              >
                Fechar
              </button>
            </div>
          </div>
        ) : null}
      </aside>
    </>,
    document.body,
  );
}

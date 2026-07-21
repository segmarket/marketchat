import { useEffect, useRef, useState } from "react";
import { Receipt, Send } from "lucide-react";
import { toast } from "sonner";
import Switch from "../form/switch/Switch";
import ChargePixModal from "./ChargePixModal";
import TypingIndicator from "./TypingIndicator";
import { formatAttendanceDateTime } from "../../features/chatLogs/format";
import {
  fetchConversation,
  sendAgentMessage,
  toggleSessionBot,
} from "../../features/chatLogs/api";
import { markSessionSeen } from "../../features/chatLogs/inboxUnread";
import type { ChatConversationResponse, ChatLogMessage } from "../../features/chatLogs/types";
import { formatPhoneBR } from "../../features/residents/format";
import { getAxiosErrorMessage } from "../../utils/apiError";
import { useModal } from "../../hooks/useModal";

type Props = {
  sessionId: number | null;
  onBotStatusChange?: (sessionId: number, isBotActive: boolean) => void;
  onSeenUpdate?: () => void;
};

function bubbleClass(direction: string): string {
  if (direction === "INBOUND") {
    return "rounded-bl-sm bg-emerald-100 text-emerald-950";
  }
  if (direction === "AGENT") {
    return "rounded-br-sm bg-brand-500 text-white";
  }
  return "rounded-br-sm bg-gray-200 text-gray-800 dark:bg-gray-800 dark:text-gray-100";
}

function directionLabel(direction: string): string {
  if (direction === "INBOUND") return "Morador";
  if (direction === "AGENT") return "Você";
  return "Bot";
}

function maxMessageId(messages: ChatLogMessage[]): number {
  let max = 0;
  for (const m of messages) {
    if (m.id > max) max = m.id;
  }
  return max;
}

function playNotifySound(): void {
  try {
    const audio = new Audio("/sounds/notify.mp3");
    void audio.play().catch(() => {
      // autoplay bloqueado pelo browser
    });
  } catch {
    // ignore
  }
}

export default function InboxChatPane({
  sessionId,
  onBotStatusChange,
  onSeenUpdate,
}: Props) {
  const [loading, setLoading] = useState(false);
  const [conversation, setConversation] = useState<ChatConversationResponse | null>(null);
  const [draft, setDraft] = useState("");
  const [toggling, setToggling] = useState(false);
  const [sending, setSending] = useState(false);
  const [isTyping, setIsTyping] = useState(false);
  const chargeModal = useModal();

  const scrollRef = useRef<HTMLDivElement>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const stickToBottomRef = useRef(true);
  const knownMaxIdRef = useRef(0);
  const readyToPollRef = useRef(false);
  const sessionIdRef = useRef(sessionId);
  const onSeenUpdateRef = useRef(onSeenUpdate);
  const onBotStatusChangeRef = useRef(onBotStatusChange);
  const lastReportedBotActiveRef = useRef<boolean | null>(null);

  sessionIdRef.current = sessionId;
  onSeenUpdateRef.current = onSeenUpdate;
  onBotStatusChangeRef.current = onBotStatusChange;

  const messageCount = conversation?.messages.length ?? 0;

  function markSeenFromMessages(sid: number, messages: ChatLogMessage[]) {
    const maxId = maxMessageId(messages);
    if (maxId <= 0) return;
    if (markSessionSeen(sid, maxId)) {
      onSeenUpdateRef.current?.();
    }
  }

  function reportBotStatus(sid: number, isBotActive: boolean) {
    if (lastReportedBotActiveRef.current === isBotActive) return;
    lastReportedBotActiveRef.current = isBotActive;
    onBotStatusChangeRef.current?.(sid, isBotActive);
  }

  // Auto-scroll após paint quando o número de mensagens muda.
  useEffect(() => {
    if (messageCount <= 0) return;
    if (!stickToBottomRef.current) return;
    const el = scrollRef.current;
    if (el) {
      el.scrollTop = el.scrollHeight;
    } else {
      messagesEndRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
    }
  }, [messageCount, sessionId]);

  // Mostra o indicador de digitação sem quebrar o stick-to-bottom.
  useEffect(() => {
    if (!isTyping) return;
    if (!stickToBottomRef.current) return;
    const el = scrollRef.current;
    if (el) {
      el.scrollTop = el.scrollHeight;
    }
  }, [isTyping]);

  // Carga completa só quando a sessão selecionada muda (evita loop de re-fetch).
  useEffect(() => {
    if (sessionId == null) {
      setConversation(null);
      setDraft("");
      setIsTyping(false);
      knownMaxIdRef.current = 0;
      readyToPollRef.current = false;
      lastReportedBotActiveRef.current = null;
      return;
    }

    const sid = sessionId;
    let cancelled = false;

    async function loadFull() {
      setLoading(true);
      setConversation(null);
      setDraft("");
      setIsTyping(false);
      knownMaxIdRef.current = 0;
      readyToPollRef.current = false;
      stickToBottomRef.current = true;
      lastReportedBotActiveRef.current = null;
      try {
        const data = await fetchConversation(sid);
        if (cancelled || sessionIdRef.current !== sid) return;
        setConversation(data);
        setIsTyping(Boolean(data.client_is_typing));
        knownMaxIdRef.current = maxMessageId(data.messages);
        readyToPollRef.current = true;
        markSeenFromMessages(sid, data.messages);
        reportBotStatus(sid, data.is_bot_active);
      } catch (err) {
        if (cancelled || sessionIdRef.current !== sid) return;
        toast.error(
          getAxiosErrorMessage(err, {
            notAxiosMessage: "Não foi possível carregar a conversa.",
          }),
        );
        setConversation(null);
      } finally {
        if (!cancelled && sessionIdRef.current === sid) setLoading(false);
      }
    }

    void loadFull();
    return () => {
      cancelled = true;
    };
  }, [sessionId]);

  // Polling incremental a cada 5s (só com aba visível)
  useEffect(() => {
    if (sessionId == null) return;

    const tick = async () => {
      if (document.visibilityState !== "visible") return;
      const sid = sessionIdRef.current;
      if (sid == null) return;
      if (!readyToPollRef.current) return;
      const afterId = knownMaxIdRef.current;

      try {
        const data = await fetchConversation(
          sid,
          afterId > 0 ? { afterId } : {},
        );
        if (sessionIdRef.current !== sid) return;

        reportBotStatus(sid, data.is_bot_active);
        setIsTyping(Boolean(data.client_is_typing));

        if (afterId > 0 && data.messages.length === 0) {
          setConversation((prev) => {
            if (!prev || prev.session_id !== sid) return prev;
            if (
              prev.is_bot_active === data.is_bot_active
              && prev.last_human_interaction_at === data.last_human_interaction_at
            ) {
              return prev;
            }
            return {
              ...prev,
              is_bot_active: data.is_bot_active,
              last_human_interaction_at: data.last_human_interaction_at,
            };
          });
          return;
        }

        if (data.messages.length === 0) return;

        const newInbound = data.messages.some(
          (m) => m.direction === "INBOUND" && m.id > afterId,
        );
        if (newInbound) playNotifySound();

        setConversation((prev) => {
          if (!prev || prev.session_id !== sid || afterId <= 0) {
            return { ...data, messages: data.messages };
          }
          const existing = new Set(prev.messages.map((m) => m.id));
          const merged = [
            ...prev.messages,
            ...data.messages.filter((m) => !existing.has(m.id)),
          ];
          return {
            ...prev,
            is_bot_active: data.is_bot_active,
            last_human_interaction_at: data.last_human_interaction_at,
            resident_name: data.resident_name || prev.resident_name,
            resident_phone: data.resident_phone || prev.resident_phone,
            market_name: data.market_name || prev.market_name,
            messages: merged,
          };
        });

        knownMaxIdRef.current = Math.max(afterId, maxMessageId(data.messages));
        markSeenFromMessages(sid, data.messages);
      } catch {
        // silencioso no poll
      }
    };

    const id = window.setInterval(() => {
      void tick();
    }, 5000);
    return () => window.clearInterval(id);
  }, [sessionId]);

  function handleScroll() {
    const el = scrollRef.current;
    if (!el) return;
    const distance = el.scrollHeight - el.scrollTop - el.clientHeight;
    stickToBottomRef.current = distance < 80;
  }

  const isBotActive = conversation?.is_bot_active ?? true;

  async function handleToggleBot(checked: boolean) {
    if (!conversation || toggling) return;
    const previous = conversation;
    setConversation({
      ...conversation,
      is_bot_active: checked,
      last_human_interaction_at: checked
        ? conversation.last_human_interaction_at
        : new Date().toISOString(),
    });
    reportBotStatus(conversation.session_id, checked);
    setToggling(true);
    try {
      const data = await toggleSessionBot(conversation.session_id, checked);
      setConversation({
        ...conversation,
        is_bot_active: data.is_bot_active,
        last_human_interaction_at: data.last_human_interaction_at,
      });
      reportBotStatus(conversation.session_id, data.is_bot_active);
    } catch (err) {
      setConversation(previous);
      lastReportedBotActiveRef.current = null;
      reportBotStatus(previous.session_id, previous.is_bot_active);
      toast.error(
        getAxiosErrorMessage(err, {
          notAxiosMessage: "Não foi possível alterar o status do bot.",
        }),
      );
    } finally {
      setToggling(false);
    }
  }

  async function handleSend() {
    if (!conversation || sending) return;
    const text = draft.trim();
    if (!text) return;

    setSending(true);
    try {
      const data = await sendAgentMessage(conversation.session_id, text);
      const nextMessages = data.message
        ? [...conversation.messages, data.message]
        : conversation.messages;
      if (data.message) {
        knownMaxIdRef.current = Math.max(knownMaxIdRef.current, data.message.id);
        if (markSessionSeen(conversation.session_id, data.message.id)) {
          onSeenUpdateRef.current?.();
        }
      }
      stickToBottomRef.current = true;
      setConversation({
        ...conversation,
        is_bot_active: data.is_bot_active,
        last_human_interaction_at: data.last_human_interaction_at,
        messages: nextMessages,
      });
      reportBotStatus(conversation.session_id, data.is_bot_active);
      setDraft("");
    } catch (err) {
      toast.error(
        getAxiosErrorMessage(err, {
          notAxiosMessage: "Não foi possível enviar a mensagem.",
        }),
      );
    } finally {
      setSending(false);
    }
  }

  if (sessionId == null) {
    return (
      <div className="flex h-full min-h-0 flex-1 items-center justify-center overflow-hidden bg-gray-50 dark:bg-gray-950">
        <p className="text-sm text-gray-500">
          Selecione uma conversa para atender.
        </p>
      </div>
    );
  }

  return (
    <div className="flex h-full min-h-0 flex-1 flex-col overflow-hidden bg-white dark:bg-gray-900">
      <header className="flex shrink-0 items-start justify-between gap-3 border-b border-gray-200 px-5 py-4 dark:border-gray-800">
        <div className="min-w-0 flex-1">
          <h2 className="truncate text-lg font-semibold text-gray-800 dark:text-white/90">
            {conversation?.resident_name || "Atendimento"}
          </h2>
          <p className="truncate text-sm text-gray-500">
            {conversation?.market_name || "—"}
          </p>
          {conversation?.resident_phone ? (
            <p className="mt-1 text-xs text-gray-400">
              {formatPhoneBR(conversation.resident_phone)}
            </p>
          ) : null}
          {conversation && !loading ? (
            <div className="mt-3">
              <Switch
                label={isBotActive ? "Bot Ativo" : "Atendimento Humano"}
                checked={isBotActive}
                disabled={toggling}
                onChange={handleToggleBot}
              />
            </div>
          ) : null}
        </div>
      </header>

      <div
        ref={scrollRef}
        onScroll={handleScroll}
        className="min-h-0 flex-1 space-y-3 overflow-y-auto bg-gray-50 p-4 dark:bg-gray-950"
      >
        {loading ? (
          <p className="text-sm text-gray-500">Carregando mensagens…</p>
        ) : (
          conversation?.messages.map((msg) => {
            const inbound = msg.direction === "INBOUND";
            return (
              <div
                key={msg.id}
                className={`flex ${inbound ? "justify-start" : "justify-end"}`}
              >
                <div
                  className={`max-w-[85%] rounded-2xl px-3 py-2 text-sm shadow-sm ${bubbleClass(msg.direction)}`}
                >
                  <p className="mb-1 text-[10px] font-semibold uppercase tracking-wide opacity-70">
                    {directionLabel(msg.direction)}
                  </p>
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
          <p className="text-sm text-gray-500">Nenhuma mensagem nesta conversa.</p>
        ) : null}
        <TypingIndicator visible={isTyping} />
        <div ref={messagesEndRef} />
      </div>

      {conversation && !loading ? (
        <footer className="shrink-0 border-t border-gray-200 bg-white p-4 dark:border-gray-800 dark:bg-gray-900">
          <div className="flex items-end gap-2">
            <button
              type="button"
              onClick={chargeModal.openModal}
              disabled={sending}
              className="inline-flex h-11 min-w-[44px] items-center justify-center rounded-xl border border-gray-200 bg-white text-gray-600 transition-colors hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-50 dark:border-gray-700 dark:bg-gray-950 dark:text-gray-300 dark:hover:bg-white/5"
              aria-label="Gerar cobrança PIX"
              title="Gerar cobrança PIX"
            >
              <Receipt className="size-4" />
            </button>
            <textarea
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              rows={2}
              placeholder="Escreva uma mensagem para o morador…"
              className="min-h-[44px] flex-1 resize-none rounded-xl border border-gray-200 bg-white px-3 py-2 text-sm text-gray-800 outline-none focus:border-brand-400 focus:ring-2 focus:ring-brand-100 dark:border-gray-700 dark:bg-gray-950 dark:text-white/90"
              disabled={sending}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  void handleSend();
                }
              }}
            />
            <button
              type="button"
              onClick={() => void handleSend()}
              disabled={sending || !draft.trim()}
              className="inline-flex h-11 min-w-[44px] items-center justify-center rounded-xl bg-brand-500 px-3 text-white transition-colors hover:bg-brand-600 disabled:cursor-not-allowed disabled:opacity-50"
              aria-label="Enviar mensagem"
            >
              <Send className="size-4" />
            </button>
          </div>
          <p className="mt-2 text-xs text-gray-500">
            Ao enviar, o bot é pausado automaticamente. Ele reativa após 2h sem
            interação humana.
          </p>
        </footer>
      ) : null}

      {sessionId != null ? (
        <ChargePixModal
          open={chargeModal.isOpen}
          sessionId={sessionId}
          onClose={chargeModal.closeModal}
          onInsertDraft={(text) => {
            setDraft(text);
            stickToBottomRef.current = true;
          }}
        />
      ) : null}
    </div>
  );
}

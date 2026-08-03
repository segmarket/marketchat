import { FormEvent, useEffect, useRef, useState } from "react";
import { Camera, ImageIcon, RotateCcw } from "lucide-react";
import { api } from "../../services/api";

type ChatRole = "user" | "bot" | "system";

type ChatMessage = {
  id: string;
  role: ChatRole;
  text: string;
  kind?: "text" | "media";
};

const SESSION_KEY = "mc_demo_session";
const MEDIA_PAYLOAD = "[MEDIA:IMAGE]";
const WELCOME_TEXT =
  "Olá! Sou o assistente do Mercado Portal. Pode se apresentar, pedir um produto ou testar um dos cenários ao lado.";
const CONNECTION_FALLBACK_MESSAGE =
  "Poxa, parece que minha conexão falhou por um instante. Você pode repetir, por favor?";

function newSessionId(): string {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID();
  }
  return `${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
}

function welcomeMessage(): ChatMessage {
  return { id: "welcome", role: "bot", text: WELCOME_TEXT };
}

export const DEMO_CHAT_SUGGESTIONS = [
  {
    label: "Comprar (com erro)",
    text: "Quero uma coquinha e sucrilos",
  },
  {
    label: "Reclamação",
    text: "O leite que comprei ontem estava vencido, um absurdo!",
  },
  {
    label: "Anti-Spam",
    text: "Olá, fazemos projetos 3D para mercadinhos, qual o valor?",
  },
  {
    label: "Chamar Humano",
    text: "Robô inútil, me passa pra um atendente agora",
  },
] as const;

export type WhatsAppDemoChatProps = {
  draft?: string;
  onDraftChange?: (value: string) => void;
  /** Incrementar dispara envio de mídia simulada (atalho da coluna esquerda). */
  mediaTrigger?: number;
  className?: string;
};

function splitBotReply(reply: string): string[] {
  return reply
    .split(/\n\n+/)
    .map((part) => part.trim())
    .filter(Boolean);
}

function newId(): string {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
}

export default function WhatsAppDemoChat({
  draft,
  onDraftChange,
  mediaTrigger = 0,
  className = "",
}: WhatsAppDemoChatProps) {
  const isControlled = typeof onDraftChange === "function";
  const [internalInput, setInternalInput] = useState("");
  const input = isControlled ? (draft ?? "") : internalInput;
  const setInput = isControlled ? onDraftChange! : setInternalInput;

  const [messages, setMessages] = useState<ChatMessage[]>([welcomeMessage()]);
  const [sessionId, setSessionId] = useState("");
  const [typing, setTyping] = useState(false);
  const [error, setError] = useState("");
  const messagesContainerRef = useRef<HTMLDivElement | null>(null);
  const lastMediaTriggerRef = useRef(0);
  const typingRef = useRef(false);
  const sessionIdRef = useRef(sessionId);
  const isInitialMount = useRef(true);

  useEffect(() => {
    typingRef.current = typing;
  }, [typing]);

  useEffect(() => {
    sessionIdRef.current = sessionId;
  }, [sessionId]);

  useEffect(() => {
    const existing = localStorage.getItem(SESSION_KEY) || "";
    setSessionId(existing);
  }, []);

  useEffect(() => {
    const container = messagesContainerRef.current;
    if (!container) return;

    if (isInitialMount.current) {
      isInitialMount.current = false;
      return;
    }

    // Só rola o painel interno — nunca scrollIntoView (evita puxar a window)
    container.scrollTo({ top: container.scrollHeight, behavior: "smooth" });
  }, [messages, typing]);

  function handleReset(options?: { announce?: boolean }) {
    const nextId = newSessionId();
    setSessionId(nextId);
    sessionIdRef.current = nextId;
    localStorage.setItem(SESSION_KEY, nextId);
    setError("");
    setTyping(false);
    if (options?.announce) {
      setMessages([
        welcomeMessage(),
        {
          id: newId(),
          role: "bot",
          text: "Chat reiniciado com sucesso! Como posso te ajudar?",
        },
      ]);
    } else {
      setMessages([welcomeMessage()]);
    }
  }

  function appendBotReplies(reply: string) {
    const bubbles = splitBotReply(reply || "");
    if (bubbles.length === 0) {
      setMessages((prev) => [
        ...prev,
        {
          id: newId(),
          role: "bot",
          text: CONNECTION_FALLBACK_MESSAGE,
        },
      ]);
      return;
    }
    setMessages((prev) => [
      ...prev,
      ...bubbles.map((part) => ({
        id: newId(),
        role: "bot" as const,
        text: part,
      })),
    ]);
  }

  async function sendSimulatedMedia() {
    if (typingRef.current) return;

    setError("");
    setMessages((prev) => [
      ...prev,
      {
        id: newId(),
        role: "user",
        text: "[Imagem Simulada]",
        kind: "media",
      },
    ]);
    setTyping(true);

    try {
      const { data } = await api.post<{ reply: string; session_id: string }>(
        "/api/demo/chat/",
        {
          message: MEDIA_PAYLOAD,
          is_media: true,
          session_id: sessionIdRef.current || undefined,
        },
      );
      const nextSession = data.session_id || sessionIdRef.current;
      if (nextSession) {
        setSessionId(nextSession);
        localStorage.setItem(SESSION_KEY, nextSession);
      }
      appendBotReplies(data.reply || "");
    } catch {
      setError("");
      appendBotReplies("");
    } finally {
      setTyping(false);
    }
  }

  useEffect(() => {
    if (!mediaTrigger || mediaTrigger === lastMediaTriggerRef.current) return;
    lastMediaTriggerRef.current = mediaTrigger;
    void sendSimulatedMedia();
  }, [mediaTrigger]);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    const text = input.trim();
    if (!text || typing) return;

    if (text.toLowerCase() === "reiniciar") {
      setInput("");
      handleReset({ announce: true });
      return;
    }

    setInput("");
    setError("");
    setMessages((prev) => [...prev, { id: newId(), role: "user", text }]);
    setTyping(true);

    try {
      const { data } = await api.post<{ reply: string; session_id: string }>(
        "/api/demo/chat/",
        { message: text, session_id: sessionId || undefined },
      );
      const nextSession = data.session_id || sessionId;
      if (nextSession) {
        setSessionId(nextSession);
        localStorage.setItem(SESSION_KEY, nextSession);
      }
      appendBotReplies(data.reply || "");
    } catch {
      setError("");
      appendBotReplies("");
    } finally {
      setTyping(false);
    }
  }

  return (
    <div className={`mx-auto flex w-full max-w-full flex-col gap-3 md:max-w-[400px] ${className}`}>
      <div
        className="flex h-[600px] max-h-[60dvh] w-full flex-col overflow-hidden rounded-2xl border-0 bg-[#ECE5DD] shadow-md md:h-[min(750px,85dvh)] md:max-h-[750px] md:rounded-[3rem] md:border-[12px] md:border-slate-800 md:bg-slate-800 md:shadow-2xl"
      >
        <div className="flex min-h-0 flex-1 flex-col overflow-hidden rounded-2xl bg-[#ECE5DD] md:rounded-[2.1rem]">
          <div className="flex shrink-0 items-start justify-between gap-2 bg-[#075E54] px-4 py-3.5">
            <div className="min-w-0">
              <p className="text-sm font-semibold text-white">Bem-vindo ao Mercado Portal</p>
              <p className="text-xs text-white/80">online · demonstração</p>
            </div>
            <button
              type="button"
              onClick={() => handleReset()}
              disabled={typing}
              className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-white/90 transition hover:bg-white/10 disabled:opacity-50"
              aria-label="Reiniciar conversa"
              title="Reiniciar conversa"
            >
              <RotateCcw className="h-[18px] w-[18px]" aria-hidden />
            </button>
          </div>

          <div
            ref={messagesContainerRef}
            className="min-h-0 flex-1 space-y-2 overflow-y-auto overscroll-contain px-3 py-3"
          >
            {messages.map((msg) => {
              if (msg.role === "system") {
                return (
                  <div
                    key={msg.id}
                    className="mx-auto max-w-[90%] rounded-lg bg-black/5 px-3 py-1.5 text-center text-xs italic text-gray-500"
                  >
                    {msg.text}
                  </div>
                );
              }
              if (msg.kind === "media" && msg.role === "user") {
                return (
                  <div
                    key={msg.id}
                    className="ml-auto flex max-w-[88%] items-center gap-2 rounded-lg rounded-tr-none bg-[#DCF8C6] px-3 py-2 text-sm text-gray-800 shadow-sm"
                  >
                    <span className="flex h-10 w-10 items-center justify-center rounded-md bg-black/5 text-[#075E54]">
                      <ImageIcon className="h-5 w-5" aria-hidden />
                    </span>
                    <span className="font-medium">{msg.text}</span>
                  </div>
                );
              }
              return (
                <div
                  key={msg.id}
                  className={
                    msg.role === "user"
                      ? "ml-auto max-w-[88%] rounded-lg rounded-tr-none bg-[#DCF8C6] px-3 py-2 text-sm text-gray-800 shadow-sm whitespace-pre-wrap"
                      : "max-w-[88%] rounded-lg rounded-tl-none bg-white px-3 py-2 text-sm text-gray-800 shadow-sm whitespace-pre-wrap"
                  }
                >
                  {msg.text}
                </div>
              );
            })}
            {typing && (
              <div className="max-w-[70%] rounded-lg rounded-tl-none bg-white px-3 py-2 text-sm text-gray-500 shadow-sm">
                digitando…
              </div>
            )}
            <div aria-hidden />
          </div>

          <form
            onSubmit={handleSubmit}
            className="flex shrink-0 items-center gap-1.5 border-t border-black/5 bg-[#F0F0F0] px-2 py-2.5"
          >
            <button
              type="button"
              onClick={() => void sendSimulatedMedia()}
              disabled={typing}
              className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full text-[#075E54] transition hover:bg-black/5 disabled:opacity-50"
              aria-label="Simular envio de foto"
              title="Simular envio de foto"
            >
              <Camera className="h-5 w-5" aria-hidden />
            </button>
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Digite uma mensagem"
              className="min-w-0 flex-1 rounded-full border-0 bg-white px-3 py-2.5 text-base text-gray-800 shadow-sm outline-none ring-1 ring-black/5 placeholder:text-gray-400"
              maxLength={2000}
              disabled={typing}
              aria-label="Mensagem do demo"
            />
            <button
              type="submit"
              disabled={typing || !input.trim()}
              className="rounded-full bg-[#075E54] px-3.5 py-2.5 text-xs font-semibold text-white disabled:opacity-50"
            >
              Enviar
            </button>
          </form>
        </div>
      </div>

      {error ? <p className="text-center text-xs text-red-600">{error}</p> : null}
      <p className="text-center text-[11px] text-gray-500">
        Demo isolada — não envia WhatsApp real.
      </p>
    </div>
  );
}

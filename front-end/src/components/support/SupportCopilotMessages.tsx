import type { SupportChatMessage } from "../../features/supportCopilot/types";

export function TypingIndicator() {
  return (
    <div className="flex justify-start">
      <div className="flex items-center gap-1 rounded-2xl rounded-bl-sm bg-gray-100/90 px-4 py-3 dark:bg-gray-800/90">
        <span className="size-2 animate-bounce rounded-full bg-gray-400 [animation-delay:0ms]" />
        <span className="size-2 animate-bounce rounded-full bg-gray-400 [animation-delay:150ms]" />
        <span className="size-2 animate-bounce rounded-full bg-gray-400 [animation-delay:300ms]" />
      </div>
    </div>
  );
}

type Props = {
  messages: SupportChatMessage[];
  loading: boolean;
  onOpenTicket: () => void;
};

export default function SupportCopilotMessages({ messages, loading, onOpenTicket }: Props) {
  return (
    <>
      {messages.length === 0 && !loading ? (
        <p className="text-center text-sm text-gray-500 dark:text-gray-400">
          Pergunte sobre esta tela ou use uma sugestão acima.
        </p>
      ) : null}

      {messages.map((msg, index) => {
        const isUser = msg.role === "user";
        const showTicketLink = !isUser && !loading;
        return (
          <div key={`${msg.role}-${index}-${msg.content.slice(0, 24)}`} className="space-y-1">
            <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
              <div
                className={`max-w-[85%] rounded-2xl px-3 py-2 text-sm leading-relaxed whitespace-pre-wrap ${
                  isUser
                    ? "rounded-br-sm bg-brand-500 text-white"
                    : "rounded-bl-sm bg-gray-100/90 text-gray-800 dark:bg-gray-800/90 dark:text-gray-100"
                }`}
              >
                {msg.content}
              </div>
            </div>
            {showTicketLink ? (
              <button
                type="button"
                onClick={onOpenTicket}
                className="pl-1 text-xs text-gray-500 underline-offset-2 hover:text-brand-600 hover:underline dark:text-gray-400 dark:hover:text-brand-400"
              >
                Não resolveu? Abrir ticket
              </button>
            ) : null}
          </div>
        );
      })}

      {loading ? <TypingIndicator /> : null}
    </>
  );
}

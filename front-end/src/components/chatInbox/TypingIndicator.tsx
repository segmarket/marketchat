type Props = {
  visible: boolean;
};

export default function TypingIndicator({ visible }: Props) {
  if (!visible) return null;

  return (
    <div
      className="flex items-center gap-2 px-1 py-1 text-xs italic text-gray-500 dark:text-gray-400"
      aria-live="polite"
    >
      <span className="inline-flex items-center gap-0.5" aria-hidden>
        <span className="size-1.5 animate-bounce rounded-full bg-gray-400 [animation-delay:0ms] dark:bg-gray-500" />
        <span className="size-1.5 animate-bounce rounded-full bg-gray-400 [animation-delay:150ms] dark:bg-gray-500" />
        <span className="size-1.5 animate-bounce rounded-full bg-gray-400 [animation-delay:300ms] dark:bg-gray-500" />
      </span>
      <span>Cliente digitando…</span>
    </div>
  );
}

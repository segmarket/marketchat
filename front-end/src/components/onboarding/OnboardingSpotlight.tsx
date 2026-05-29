import { ArrowDown, ArrowUp } from "lucide-react";
import type { ReactNode } from "react";

type HighlightMode = "button" | "block";
type CalloutPlacement = "below" | "above";

type Props = {
  message: string;
  children: ReactNode;
  align?: "start" | "end" | "center";
  highlightMode?: HighlightMode;
  calloutPlacement?: CalloutPlacement;
  intense?: boolean;
};

const HIGHLIGHT_BUTTON =
  "[&_button]:relative [&_button]:z-50 [&_button]:shadow-[0_0_20px_rgba(255,255,255,0.6)] [&_button]:ring-2 [&_button]:ring-white/40";

const HIGHLIGHT_BUTTON_INTENSE =
  "[&_button]:relative [&_button]:z-50 [&_button]:shadow-[0_0_28px_rgba(255,255,255,0.85)] [&_button]:ring-2 [&_button]:ring-white/60";

const HIGHLIGHT_BLOCK =
  "relative z-50 rounded-xl shadow-[0_0_24px_rgba(255,255,255,0.75)] ring-2 ring-white/50";

export default function OnboardingSpotlight({
  message,
  children,
  align = "end",
  highlightMode = "button",
  calloutPlacement = "below",
  intense = false,
}: Props) {
  const horizontalAlign =
    align === "center"
      ? "items-center text-center"
      : align === "start"
        ? "items-start"
        : "items-end";

  const arrowOffset =
    align === "center" ? "mx-auto" : align === "end" ? "ml-auto" : "";

  const highlightClass =
    highlightMode === "block"
      ? HIGHLIGHT_BLOCK
      : intense
        ? `relative z-50 ${HIGHLIGHT_BUTTON_INTENSE}`
        : `relative z-50 ${HIGHLIGHT_BUTTON}`;

  const callout = (
    <div
      className={`flex w-72 flex-col sm:w-80 ${horizontalAlign}`}
      role="status"
    >
      {calloutPlacement === "below" ? (
        <ArrowUp
          className={`mb-1 h-6 w-6 animate-spotlight-float text-white motion-reduce:animate-none ${arrowOffset}`}
          aria-hidden
        />
      ) : null}
      <div className="rounded-xl bg-gray-900 px-4 py-3 text-sm leading-snug text-white shadow-xl dark:bg-gray-950">
        {message}
      </div>
      {calloutPlacement === "above" ? (
        <ArrowDown
          className={`mt-1 h-6 w-6 animate-spotlight-float text-white motion-reduce:animate-none ${arrowOffset}`}
          aria-hidden
        />
      ) : null}
    </div>
  );

  return (
    <>
      <div
        className="pointer-events-none fixed inset-0 z-40 bg-black/70 transition-opacity duration-300"
        aria-hidden="true"
      />

      <div className={`relative z-50 flex flex-col ${horizontalAlign}`}>
        {calloutPlacement === "above" ? callout : null}
        <div className={highlightClass}>{children}</div>
        {calloutPlacement === "below" ? callout : null}
      </div>
    </>
  );
}

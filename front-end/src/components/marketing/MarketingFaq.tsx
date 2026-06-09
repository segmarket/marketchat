import { useState } from "react";
import { Minus, Plus } from "lucide-react";
import { FAQ_ITEMS } from "../../constants/marketingCopy";

function FaqItem({ question, answer }: { question: string; answer: string }) {
  const [open, setOpen] = useState(false);

  return (
    <details
      className="group rounded-xl border border-gray-200 bg-white"
      open={open}
      onToggle={(e) => setOpen((e.target as HTMLDetailsElement).open)}
    >
      <summary
        className="flex min-h-[48px] cursor-pointer list-none items-center justify-between gap-4 px-5 py-4 text-left font-medium text-gray-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-brand-500 [&::-webkit-details-marker]:hidden"
        aria-expanded={open}
      >
        <span>{question}</span>
        <span className="shrink-0 text-brand-600" aria-hidden>
          {open ? <Minus className="h-5 w-5" /> : <Plus className="h-5 w-5" />}
        </span>
      </summary>
      <div className="border-t border-gray-100 px-5 pb-4 pt-3 text-sm leading-relaxed text-gray-600">
        {answer}
      </div>
    </details>
  );
}

export default function MarketingFaq() {
  return (
    <section id="faq" className="scroll-mt-24 bg-white px-4 py-20 sm:px-6 lg:px-8">
      <div className="mx-auto max-w-3xl">
        <div className="text-center">
          <h2 className="text-3xl font-bold text-gray-900 sm:text-4xl">Perguntas frequentes</h2>
          <p className="mt-4 text-lg text-gray-600">
            Respostas diretas para as dúvidas que mais travam a decisão de testar.
          </p>
        </div>
        <div className="mt-10 space-y-3">
          {FAQ_ITEMS.map((item) => (
            <FaqItem key={item.question} question={item.question} answer={item.answer} />
          ))}
        </div>
      </div>
    </section>
  );
}

import { Headphones, Layers, ShieldCheck, Sparkles } from "lucide-react";
import { TRUST_GUARANTEES } from "../../constants/marketingCopy";

const ICONS = [Sparkles, ShieldCheck, Layers, Headphones] as const;

export default function MarketingTrustBand() {
  return (
    <section
      aria-label="Garantias do MarketChat"
      className="border-y border-gray-200 bg-white px-4 py-10 sm:px-6 lg:px-8"
    >
      <div className="mx-auto grid max-w-7xl gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {TRUST_GUARANTEES.map((item, index) => {
          const Icon = ICONS[index] ?? ShieldCheck;
          return (
            <article
              key={item.title}
              className="flex min-h-[120px] flex-col rounded-xl border border-gray-200 bg-gray-25 p-5"
            >
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-brand-50 text-brand-600">
                <Icon className="h-5 w-5" aria-hidden />
              </div>
              <h3 className="mt-3 text-sm font-semibold text-gray-900">{item.title}</h3>
              <p className="mt-1 text-sm leading-relaxed text-gray-600">{item.description}</p>
            </article>
          );
        })}
      </div>
    </section>
  );
}

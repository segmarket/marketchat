import { Check } from "lucide-react";
import MarketingCtaLink from "./MarketingCtaLink";

const planPrice = import.meta.env.VITE_PLAN_PRICE?.trim() || "59,90";

const FEATURES = [
  "Chatbot Ilimitado",
  "Auditoria de Fotos",
  "Painel de Alertas",
  "Gestão de Múltiplos Mercados",
] as const;

export default function MarketingPricing() {
  return (
    <section id="precos" className="scroll-mt-24 bg-gray-50 px-4 py-20 sm:px-6 lg:px-8">
      <div className="mx-auto max-w-7xl">
        <div className="mx-auto max-w-2xl text-center">
          <h2 className="text-3xl font-bold text-gray-900 sm:text-4xl">
            Toda essa operação por menos que um café por dia.
          </h2>
          <p className="mt-4 text-lg text-gray-600">
            Um plano simples, com tudo que você precisa para operar o mercado autônomo. Sem
            surpresas, sem taxas ocultas.
          </p>
        </div>

        <article className="mx-auto mt-14 flex max-w-lg flex-col rounded-xl border border-brand-500 bg-white p-8 shadow-xl ring-2 ring-brand-500">
          <span className="mb-4 inline-flex w-fit rounded-full bg-brand-500 px-3 py-1 text-xs font-semibold text-white">
            Tudo incluso
          </span>
          <h3 className="text-2xl font-bold text-gray-900">Plano Pro — Tudo Incluso</h3>
          <p className="mt-6">
            <span className="text-4xl font-bold text-gray-900">R$ {planPrice}</span>
            <span className="text-gray-500"> / mês por mercado</span>
          </p>
          <p className="mt-6 text-sm leading-relaxed text-gray-600">
            Acesso total ao ecossistema: gerente virtual no WhatsApp, Photo-Lock, central de
            alertas em tempo real e gestão de vários condomínios. Comece com{" "}
            <span className="font-semibold text-gray-900">7 dias de teste totalmente gratuitos</span>
            .
          </p>
          <ul className="mt-8 space-y-3">
            {FEATURES.map((feature) => (
              <li key={feature} className="flex gap-2 text-sm text-gray-700">
                <Check className="h-5 w-5 shrink-0 text-success-600" />
                {feature}
              </li>
            ))}
          </ul>
          <MarketingCtaLink
            className="mt-8 block rounded-md bg-green-500 py-3 text-center text-sm font-semibold text-white transition-colors hover:bg-green-600"
          >
            Começar 7 Dias Grátis
          </MarketingCtaLink>
        </article>
      </div>
    </section>
  );
}

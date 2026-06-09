import { Check } from "lucide-react";
import { CTA_LOCATIONS } from "../../constants/analyticsEvents";
import MarketingCtaLink from "./MarketingCtaLink";
import {
  CTA_PRIMARY_CLASS,
  CTA_TRIAL_LONG,
  PRICING_ANCHOR_SUFFIX,
  PRICING_ANTI_FEAR,
  PRICING_HEADLINE,
  PRICING_SUBHEADLINE,
  planDailyPriceLabel,
  planPriceDisplay,
} from "../../constants/marketingCopy";

const FEATURES = [
  "Chatbot Ilimitado",
  "Auditoria de Fotos",
  "Painel de Alertas",
  "Gestão de Múltiplos Mercados",
] as const;

export default function MarketingPricing() {
  const planPrice = planPriceDisplay();
  const dailyPrice = planDailyPriceLabel();

  return (
    <section id="precos" className="scroll-mt-24 bg-gray-50 px-4 py-20 sm:px-6 lg:px-8">
      <div className="mx-auto max-w-7xl">
        <div className="mx-auto max-w-2xl text-center">
          <h2 className="text-3xl font-bold text-gray-900 sm:text-4xl">{PRICING_HEADLINE}</h2>
          <p className="mt-4 text-lg text-gray-600">{PRICING_SUBHEADLINE}</p>
        </div>

        <article className="mx-auto mt-14 flex max-w-lg flex-col rounded-xl border border-brand-500 bg-white p-8 shadow-xl ring-2 ring-brand-500">
          <span className="mb-4 inline-flex w-fit rounded-full bg-brand-500 px-3 py-1 text-xs font-semibold text-white">
            Tudo incluso
          </span>
          <h3 className="text-2xl font-bold text-gray-900">Plano Pro — Tudo Incluso</h3>
          <p className="mt-6">
            <span className="text-4xl font-bold text-gray-900">R$ {planPrice}</span>
            <span className="text-gray-600"> / mês por mercado</span>
          </p>
          <p className="mt-2 text-sm font-medium text-brand-700">{dailyPrice}</p>
          <p className="mt-1 text-sm text-gray-600">{PRICING_ANCHOR_SUFFIX}</p>
          <p className="mt-6 text-sm leading-relaxed text-gray-600">
            Acesso total ao ecossistema: gerente virtual no WhatsApp, Photo-Lock, central de
            alertas em tempo real e gestão de vários condomínios. Comece com{" "}
            <span className="font-semibold text-gray-900">7 dias de teste totalmente gratuitos</span>
            .
          </p>
          <ul className="mt-8 space-y-3">
            {FEATURES.map((feature) => (
              <li key={feature} className="flex gap-2 text-sm text-gray-700">
                <Check className="h-5 w-5 shrink-0 text-success-600" aria-hidden />
                {feature}
              </li>
            ))}
          </ul>
          <MarketingCtaLink
            className={`mt-8 block w-full text-center ${CTA_PRIMARY_CLASS}`}
            analyticsLocation={CTA_LOCATIONS.PRICING}
          >
            {CTA_TRIAL_LONG}
          </MarketingCtaLink>
          <p className="mt-4 text-center text-sm leading-relaxed text-gray-600">{PRICING_ANTI_FEAR}</p>
        </article>
      </div>
    </section>
  );
}

import { Check } from "lucide-react";
import { appUrl } from "../../utils/host";

const trialPrice =
  import.meta.env.VITE_TRIAL_SUBSCRIPTION_PRICE?.trim() || "29,90";

const PLANS = [
  {
    name: "Starter",
    description: "Ideal para 1 condomínio começando com mercado autônomo.",
    price: `R$ ${trialPrice}`,
    period: "/mês",
    highlighted: false,
    features: [
      "1 mercado / condomínio",
      "WhatsApp + IA de busca",
      "Photo-Lock e Pix Asaas",
      "Painel operacional completo",
    ],
  },
  {
    name: "Scale",
    description: "Para redes de mercados autônomos em múltiplos condomínios.",
    price: "Sob consulta",
    period: "",
    highlighted: true,
    features: [
      "Múltiplos mercados",
      "Suporte prioritário",
      "Métricas consolidadas",
      "Sem taxas abusivas de apps terceiros",
    ],
  },
] as const;

export default function MarketingPricing() {
  return (
    <section id="precos" className="scroll-mt-24 bg-gray-50 px-4 py-20 sm:px-6 lg:px-8">
      <div className="mx-auto max-w-7xl">
        <div className="mx-auto max-w-2xl text-center">
          <h2 className="text-3xl font-bold text-gray-900 sm:text-4xl">Planos simples</h2>
          <p className="mt-4 text-lg text-gray-600">
            Baixo custo operacional. Você fica com o faturamento — sem intermediários que comem sua
            margem.
          </p>
        </div>

        <div className="mt-14 grid gap-8 md:grid-cols-2 lg:mx-auto lg:max-w-4xl">
          {PLANS.map((plan) => (
            <article
              key={plan.name}
              className={`flex flex-col rounded-xl border p-8 ${
                plan.highlighted
                  ? "border-brand-500 bg-white shadow-xl ring-2 ring-brand-500"
                  : "border-gray-200 bg-white shadow-sm"
              }`}
            >
              {plan.highlighted && (
                <span className="mb-4 inline-flex w-fit rounded-full bg-brand-500 px-3 py-1 text-xs font-semibold text-white">
                  Mais popular
                </span>
              )}
              <h3 className="text-xl font-bold text-gray-900">{plan.name}</h3>
              <p className="mt-2 text-sm text-gray-600">{plan.description}</p>
              <p className="mt-6">
                <span className="text-4xl font-bold text-gray-900">{plan.price}</span>
                {plan.period && (
                  <span className="text-gray-500">{plan.period}</span>
                )}
              </p>
              <ul className="mt-8 flex-1 space-y-3">
                {plan.features.map((feature) => (
                  <li key={feature} className="flex gap-2 text-sm text-gray-700">
                    <Check className="h-5 w-5 shrink-0 text-success-600" />
                    {feature}
                  </li>
                ))}
              </ul>
              <a
                href={appUrl("/register")}
                className={`mt-8 block rounded-md py-3 text-center text-sm font-semibold transition-colors ${
                  plan.highlighted
                    ? "bg-brand-500 text-white hover:bg-brand-600"
                    : "border border-brand-500 text-brand-600 hover:bg-brand-50"
                }`}
              >
                Começar agora
              </a>
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}

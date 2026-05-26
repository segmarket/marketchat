import { getAppUrl } from "../../utils/host";
import ChatMockup from "./ChatMockup";
import DashboardMockup from "./DashboardMockup";

export default function MarketingHero() {
  return (
    <section className="relative overflow-hidden bg-gradient-to-b from-brand-25 to-white px-4 py-16 sm:px-6 sm:py-24 lg:px-8">
      <div className="mx-auto grid max-w-7xl items-center gap-12 lg:grid-cols-2 lg:gap-16">
        <div>
          <p className="mb-4 inline-flex rounded-full bg-brand-50 px-3 py-1 text-sm font-medium text-brand-700 ring-1 ring-brand-200">
            Ecossistema para mercados autônomos
          </p>
          <h1 className="text-4xl font-bold leading-tight tracking-tight text-gray-900 sm:text-5xl lg:text-[3.25rem] lg:leading-[1.15]">
            Muito mais que um checkout. O gerente virtual do seu mercado autônomo operando 24
            horas por dia.
          </h1>
          <p className="mt-6 text-lg leading-relaxed text-gray-600">
            Venda pelo WhatsApp, monitore rupturas de estoque, receba alertas de infraestrutura em
            tempo real e deixe nossa Inteligência Artificial lidar com o suporte dos moradores.
            Tudo em um único painel.
          </p>
          <a
            href={getAppUrl("/signin")}
            className="mt-8 inline-flex animate-pulse items-center justify-center rounded-md bg-green-500 px-8 py-4 text-lg font-semibold text-white shadow-md transition-all hover:bg-green-600"
          >
            Começar 7 Dias Grátis
          </a>
        </div>

        <div className="relative flex items-center justify-center gap-4 lg:justify-end">
          <div className="relative z-10 -mr-8 sm:-mr-12">
            <ChatMockup />
          </div>
          <div className="relative z-20 hidden translate-y-8 sm:block">
            <DashboardMockup />
          </div>
        </div>
      </div>
    </section>
  );
}

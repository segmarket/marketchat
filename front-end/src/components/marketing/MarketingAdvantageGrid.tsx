import { BarChart3, Camera, MessageCircle, Sparkles } from "lucide-react";

const ADVANTAGES = [
  {
    icon: MessageCircle,
    title: "Barreira Zero (Sem Downloads)",
    description:
      "O morador compra pelo aplicativo que ele já abre dezenas de vezes por dia. Ativação imediata da base de clientes.",
  },
  {
    icon: Sparkles,
    title: "Busca Flexível por IA",
    description:
      'O motor inteligente entende termos parciais e sinônimos casuais (ex.: se digitar "coquinha zero", o sistema acha o produto "Coca Cola Lata Zero 350ml").',
  },
  {
    icon: Camera,
    title: "Auditoria por Photo-Lock",
    description:
      "Segurança máxima contra furtos. O robô exige uma foto real dos itens antes de liberar o Pix Copia e Cola do Asaas.",
  },
  {
    icon: BarChart3,
    title: "Painel de Saúde Operacional",
    description:
      "Gráficos intuitivos de taxa de retenção do robô, picos de acesso por faixa horária e alertas críticos instantâneos no cabeçalho.",
  },
] as const;

export default function MarketingAdvantageGrid() {
  return (
    <section id="funcionalidades" className="scroll-mt-24 bg-white px-4 py-20 sm:px-6 lg:px-8">
      <div className="mx-auto max-w-7xl">
        <div className="mx-auto max-w-2xl text-center">
          <h2 className="text-3xl font-bold text-gray-900 sm:text-4xl">
            The MarketChat Advantage
          </h2>
          <p className="mt-4 text-lg text-gray-600">
            Tecnologia pensada para mercados autônomos em condomínios — sem fricção para o morador
            nem para o operador.
          </p>
        </div>

        <div className="mt-14 grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
          {ADVANTAGES.map((item) => (
            <article
              key={item.title}
              className="rounded-xl border border-gray-200 bg-gray-25 p-6 transition-shadow hover:shadow-lg"
            >
              <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-brand-50 text-brand-600">
                <item.icon className="h-6 w-6" aria-hidden />
              </div>
              <h3 className="mt-4 text-lg font-semibold text-gray-900">{item.title}</h3>
              <p className="mt-2 text-sm leading-relaxed text-gray-600">{item.description}</p>
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}

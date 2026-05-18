import { Camera, CreditCard, Handshake, ShoppingBag } from "lucide-react";

const STEPS = [
  {
    icon: Handshake,
    title: "Saudação Humana",
    description:
      'O morador diz "Oi" e a IA responde na hora pelo nome dele e o contexto do condomínio correspondente.',
  },
  {
    icon: ShoppingBag,
    title: "Seleção Livre",
    description:
      "Ele digita o que deseja ou adiciona mais itens de forma natural no texto.",
  },
  {
    icon: Camera,
    title: "Trava de Segurança",
    description:
      "O cliente tira uma foto da sacola. O sistema registra no histórico e ativa o modal de auditoria visual com Lightbox.",
  },
  {
    icon: CreditCard,
    title: "Liquidação Instantânea",
    description:
      "O Pix do Asaas é gerado com expiração de 15 minutos. Se pago, o robô celebra e libera a saída. Se inativo, reseta o chat automaticamente.",
  },
] as const;

export default function MarketingJourney() {
  return (
    <section
      id="como-funciona"
      className="scroll-mt-24 bg-gray-50 px-4 py-20 sm:px-6 lg:px-8"
    >
      <div className="mx-auto max-w-7xl">
        <div className="mx-auto max-w-2xl text-center">
          <h2 className="text-3xl font-bold text-gray-900 sm:text-4xl">The Seamless Journey</h2>
          <p className="mt-4 text-lg text-gray-600">
            Do primeiro &quot;Oi&quot; ao Pix confirmado — sem aplicativo, sem fila, sem atrito.
          </p>
        </div>

        <ol className="mt-14 grid gap-8 md:grid-cols-2 lg:grid-cols-4">
          {STEPS.map((step, index) => (
            <li
              key={step.title}
              className="relative rounded-xl border border-gray-200 bg-white p-6 shadow-sm"
            >
              <span className="absolute -top-3 left-6 flex h-8 w-8 items-center justify-center rounded-full bg-brand-500 text-sm font-bold text-white">
                {index + 1}
              </span>
              <div className="mt-4 flex h-11 w-11 items-center justify-center rounded-lg bg-brand-50 text-brand-600">
                <step.icon className="h-5 w-5" aria-hidden />
              </div>
              <h3 className="mt-4 text-lg font-semibold text-gray-900">{step.title}</h3>
              <p className="mt-2 text-sm leading-relaxed text-gray-600">{step.description}</p>
            </li>
          ))}
        </ol>
      </div>
    </section>
  );
}

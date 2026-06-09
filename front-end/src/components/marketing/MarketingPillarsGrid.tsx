import {
  AlertTriangle,
  MessageSquareCode,
  PackageX,
  ShoppingCart,
} from "lucide-react";

const PILLARS = [
  {
    icon: ShoppingCart,
    gain: "Não perca a venda",
    title: "Vendas sem atrito e Photo-Lock",
    description:
      "Se a maquininha falhar, a IA monta o carrinho no WhatsApp e gera o Pix, exigindo foto dos produtos para auditoria de segurança.",
  },
  {
    icon: PackageX,
    gain: "Fim do estoque zerado",
    title: "Ruptura virando oportunidade",
    description:
      'A IA entende quando o morador relata falta de produtos ou validade vencida, sugere substitutos e alerta você no painel.',
  },
  {
    icon: AlertTriangle,
    gain: "Proteja seu estoque",
    title: "Alertas de equipamentos",
    description:
      "Geladeira desligada ou ar-condicionado quebrado? O bot agradece o aviso e notifica você antes da perda de mercadoria.",
  },
  {
    icon: MessageSquareCode,
    gain: "Atendimento blindado",
    title: "Suporte com tom certo",
    description:
      "Respostas amigáveis para dúvidas reais e escudo profissional contra provocações — sempre guiando para a compra.",
  },
] as const;

export default function MarketingPillarsGrid() {
  return (
    <section id="pilares" className="scroll-mt-24 bg-white px-4 py-20 sm:px-6 lg:px-8">
      <div className="mx-auto max-w-7xl">
        <div className="mx-auto max-w-2xl text-center">
          <h2 className="text-3xl font-bold text-gray-900 sm:text-4xl">
            Quatro inteligências operando o seu mercado
          </h2>
          <p className="mt-4 text-lg text-gray-600">
            Vendas, estoque, infraestrutura e suporte — o gerente virtual cuida do morador e te
            avisa quando sua atenção importa.
          </p>
        </div>

        <div className="mt-14 grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-4">
          {PILLARS.map((item) => (
            <article
              key={item.title}
              className="flex min-h-[220px] flex-col rounded-xl border border-gray-200 bg-gray-25 p-6 transition-shadow hover:shadow-lg"
            >
              <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-brand-50 text-brand-600">
                <item.icon className="h-6 w-6" aria-hidden />
              </div>
              <p className="mt-4 text-xs font-bold uppercase tracking-wide text-brand-600">
                {item.gain}
              </p>
              <h3 className="mt-1 text-lg font-semibold text-gray-900">{item.title}</h3>
              <p className="mt-2 text-sm leading-relaxed text-gray-600">{item.description}</p>
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}

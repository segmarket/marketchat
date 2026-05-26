import {
  AlertTriangle,
  MessageSquareCode,
  PackageX,
  ShoppingCart,
} from "lucide-react";

const PILLARS = [
  {
    icon: ShoppingCart,
    title: "Vendas sem Atrito e Trava por Foto",
    description:
      "Se a maquininha física falhar, não perca a venda. A IA assume, monta o carrinho no WhatsApp e gera o Pix instantâneo, exigindo a foto dos produtos para auditoria de segurança (Photo-Lock).",
  },
  {
    icon: PackageX,
    title: "Fim do Estoque Zerado",
    description:
      'A IA entende quando o morador relata falta de produtos (ex: "Acabou o leite") ou validade vencida, sugerindo itens substitutos para salvar a venda e gerando um alerta imediato no seu painel.',
  },
  {
    icon: AlertTriangle,
    title: "Alertas de Equipamentos",
    description:
      "O morador avisou que a geladeira de bebidas desligou ou o ar-condicionado quebrou? O bot agradece o feedback e notifica você imediatamente, evitando a perda de mercadorias perecíveis.",
  },
  {
    icon: MessageSquareCode,
    title: "Atendimento e Blindagem",
    description:
      "Respostas amigáveis para dúvidas reais e um escudo seco e profissional contra moradores fazendo provocações ou xingamentos. O robô coleta feedbacks de preços e guia o morador sempre para a conversão.",
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

        <div className="mt-14 grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
          {PILLARS.map((item) => (
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

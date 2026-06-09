/** Textos centralizados da landing pública (revisão de copy). */

export const MARKETING_BADGE = "Ecossistema para mercados autônomos";

export const HERO_HEADLINE = "Nunca mais perca uma venda quando a maquininha falhar.";

export const HERO_SUBTITLE =
  "O morador compra pelo WhatsApp; você recebe alertas de estoque, infraestrutura e vendas em um único painel — sem ficar preso ao caixa físico.";

export const CTA_TRIAL_PRIMARY = "Testar 7 dias grátis";
export const CTA_TRIAL_LONG = "Começar meus 7 dias grátis";
export const CTA_HOW_IT_WORKS = "Ver como funciona";

export const HERO_MICROCOPY = [
  "7 dias grátis",
  "Cancele quando quiser",
  "Cobrança só após o trial",
] as const;

export const PRICING_HEADLINE = "Toda essa operação por menos que um café por dia.";
export const PRICING_SUBHEADLINE =
  "Um plano simples, com tudo que você precisa para operar o mercado autônomo. Sem surpresas, sem taxas ocultas.";
export const PRICING_ANCHOR_SUFFIX = "Menos que o custo de uma única venda perdida.";
export const PRICING_ANTI_FEAR =
  "Não cobramos nada nos 7 dias. Você só paga se continuar — cancela em 1 clique.";

export const TRUST_GUARANTEES = [
  {
    title: "7 dias de teste gratuito",
    description: "Explore o painel e o bot no WhatsApp antes de qualquer cobrança.",
  },
  {
    title: "Sem fidelidade",
    description: "Cancele quando quiser, sem multa e sem burocracia.",
  },
  {
    title: "Vários mercados, um painel",
    description: "Gerencie todos os condomínios da sua operação no mesmo lugar.",
  },
  {
    title: "Suporte humano",
    description: "Fale com nossa equipe pelo WhatsApp quando precisar de ajuda.",
  },
] as const;

export const FAQ_ITEMS = [
  {
    question: "Preciso instalar algum equipamento?",
    answer:
      "Não. O morador usa o WhatsApp que já tem no celular. Você configura o mercado no painel e conecta o número do estabelecimento.",
  },
  {
    question: "Tem fidelidade ou multa de cancelamento?",
    answer: "Não. Você pode cancelar a assinatura quando quiser, direto no painel.",
  },
  {
    question: "Preciso de cartão para testar?",
    answer:
      "Sim, pedimos cartão para ativar o trial de 7 dias, mas só cobramos se você continuar após o período de teste. Cancele antes sem custo.",
  },
  {
    question: "Funciona com vários mercados?",
    answer:
      "Sim. Um único painel para acompanhar vendas, alertas e moradores em todos os condomínios da sua operação.",
  },
  {
    question: "A IA conversa bem com o morador?",
    answer:
      "Sim. O tom é amigável para compras e dúvidas reais, e firme e profissional em situações de provocação ou abuso.",
  },
] as const;

export const NAV_ANCHORS = [
  { label: "Pilares", href: "#pilares" },
  { label: "Para o dono", href: "#para-o-dono" },
  { label: "Preços", href: "#precos" },
  { label: "FAQ", href: "#faq" },
] as const;

export const CTA_PRIMARY_CLASS =
  "inline-flex min-h-[48px] items-center justify-center rounded-md bg-green-500 px-6 py-3 text-sm font-semibold text-white shadow-sm transition-colors hover:bg-green-600 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-green-600 focus-visible:ring-offset-2";

export const CTA_PRIMARY_LARGE_CLASS =
  "inline-flex min-h-[48px] items-center justify-center rounded-md bg-green-500 px-8 py-3.5 text-base font-semibold text-white shadow-md transition-colors hover:bg-green-600 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-green-600 focus-visible:ring-offset-2";

export const CTA_SECONDARY_CLASS =
  "inline-flex min-h-[48px] items-center justify-center rounded-md border border-gray-300 bg-white px-6 py-3 text-base font-semibold text-gray-800 transition-colors hover:bg-gray-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500 focus-visible:ring-offset-2";

export const CTA_LOGIN_LINK_CLASS =
  "rounded-sm text-sm font-medium text-gray-600 underline-offset-2 transition-colors hover:text-brand-600 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500 focus-visible:ring-offset-2";

export function planPriceDisplay(): string {
  return import.meta.env.VITE_PLAN_PRICE?.trim() || "59,90";
}

export function planDailyPriceLabel(): string {
  const raw = planPriceDisplay();
  const num = Number.parseFloat(raw.replace(",", "."));
  if (Number.isNaN(num)) return "≈ R$1,99/dia";
  const daily = num / 30;
  return `≈ R$${daily.toFixed(2).replace(".", ",")}/dia`;
}

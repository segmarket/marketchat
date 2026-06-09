import { Bell, Bot, MessageCircle, Sparkles, Target } from "lucide-react";

const STEPS = [
  {
    icon: MessageCircle,
    title: "O morador aciona o bot",
    description: "Relata um problema, busca um produto ou pede para pagar — tudo pelo WhatsApp.",
  },
  {
    icon: Sparkles,
    title: "A IA resolve no front-end",
    description:
      "Oferece alternativa de estoque, monta o carrinho com Pix ou acalma o cliente com tom profissional.",
  },
  {
    icon: Bot,
    title: "O painel recebe a tag",
    description: "Cada ocorrência vira um alerta classificado para você priorizar a ação certa.",
  },
  {
    icon: Target,
    title: "Você age com precisão",
    description: "Intervém só onde sua atenção é realmente necessária — sem ruído operacional.",
  },
] as const;

const SAMPLE_TAGS = [
  { label: "[ALERTA_ESTOQUE]", className: "bg-warning-50 text-warning-800 ring-warning-200" },
  { label: "[ALERTA_INFRA]", className: "bg-error-50 text-error-800 ring-error-200" },
  { label: "[ALERTA_QUALIDADE]", className: "bg-brand-50 text-brand-800 ring-brand-200" },
] as const;

const SAMPLE_ALERTS = [
  {
    tag: "[ALERTA_INFRA]",
    title: "Geladeira de bebidas",
    body: "Morador reportou equipamento desligado — Torre B",
    tone: "error" as const,
  },
  {
    tag: "[ALERTA_ESTOQUE]",
    title: "Leite desnatado em falta",
    body: "IA sugeriu substituto; ruptura registrada no painel",
    tone: "warning" as const,
  },
  {
    tag: "[ALERTA_QUALIDADE]",
    title: "Iogurte fora da validade",
    body: "Reclamação tratada; equipe notificada automaticamente",
    tone: "brand" as const,
  },
];

function alertStyles(tone: "error" | "warning" | "brand") {
  if (tone === "error") {
    return "border-error-200 bg-error-50";
  }
  if (tone === "warning") {
    return "border-warning-200 bg-warning-50";
  }
  return "border-brand-200 bg-brand-50";
}

export default function MarketingOwnerFlow() {
  return (
    <section
      id="para-o-dono"
      className="scroll-mt-24 bg-slate-50 px-4 py-20 sm:px-6 lg:px-8"
    >
      <div className="mx-auto max-w-7xl">
        <div className="flex flex-col gap-12 lg:grid lg:grid-cols-2 lg:items-start lg:gap-16">
          <div className="order-1">
            <h2 className="text-3xl font-bold text-gray-900 sm:text-4xl">
              Seus olhos e ouvidos dentro de cada condomínio.
            </h2>
            <p className="mt-4 text-lg text-gray-600">
              O MarketChat não substitui você — ele filtra o barulho e entrega só o que exige
              decisão humana no mercado.
            </p>

            <ol className="mt-10 space-y-6">
              {STEPS.map((step, index) => (
                <li key={step.title} className="flex gap-4">
                  <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-brand-500 text-sm font-bold text-white">
                    {index + 1}
                  </span>
                  <div>
                    <div className="flex items-center gap-2">
                      <step.icon className="h-5 w-5 text-brand-600" aria-hidden />
                      <h3 className="text-lg font-semibold text-gray-900">{step.title}</h3>
                    </div>
                    <p className="mt-1 text-sm leading-relaxed text-gray-600">
                      {step.description}
                    </p>
                    {index === 2 && (
                      <div className="mt-3 flex flex-wrap gap-2">
                        {SAMPLE_TAGS.map((tag) => (
                          <span
                            key={tag.label}
                            className={`rounded-md px-2 py-1 font-mono text-xs font-semibold ring-1 ${tag.className}`}
                          >
                            {tag.label}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                </li>
              ))}
            </ol>
          </div>

          <div className="order-2 flex justify-center lg:order-2 lg:justify-center">
            <div className="w-full max-w-xl rounded-xl border border-gray-200 bg-white p-6 shadow-lg ring-1 ring-gray-100">
              <div className="flex items-center justify-between border-b border-gray-100 pb-4">
                <div>
                  <p className="text-sm font-semibold text-gray-900">Central de alertas</p>
                  <p className="text-xs text-gray-600">Tempo real · todos os mercados</p>
                </div>
                <Bell className="h-5 w-5 text-brand-600" aria-hidden />
              </div>
              <ul className="mt-4 space-y-3">
                {SAMPLE_ALERTS.map((alert) => (
                  <li
                    key={alert.title}
                    className={`rounded-lg border px-3 py-3 ${alertStyles(alert.tone)}`}
                  >
                    <p className="font-mono text-xs font-semibold text-gray-800">{alert.tag}</p>
                    <p className="mt-1 text-sm font-medium text-gray-900">{alert.title}</p>
                    <p className="text-xs text-gray-600">{alert.body}</p>
                  </li>
                ))}
              </ul>
              <p className="mt-4 text-center text-xs text-gray-500">
                Simulação do painel — tags reais geradas pela IA em produção
              </p>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

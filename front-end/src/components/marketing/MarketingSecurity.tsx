import { Lock, ShieldCheck } from "lucide-react";

export default function MarketingSecurity() {
  return (
    <section id="seguranca" className="scroll-mt-24 bg-white px-4 py-20 sm:px-6 lg:px-8">
      <div className="mx-auto grid max-w-7xl items-center gap-12 lg:grid-cols-2">
        <div>
          <h2 className="text-3xl font-bold text-gray-900 sm:text-4xl">
            Segurança que o operador enxerga em tempo real
          </h2>
          <p className="mt-4 text-lg text-gray-600">
            Photo-Lock, auditoria visual no painel e alertas críticos no cabeçalho — tudo integrado
            ao fluxo de Pix Asaas com expiração controlada.
          </p>
          <ul className="mt-8 space-y-4">
            <li className="flex gap-3">
              <ShieldCheck className="mt-0.5 h-5 w-5 shrink-0 text-brand-600" />
              <span className="text-gray-700">
                Foto obrigatória da sacola antes de liberar o pagamento.
              </span>
            </li>
            <li className="flex gap-3">
              <Lock className="mt-0.5 h-5 w-5 shrink-0 text-brand-600" />
              <span className="text-gray-700">
                Histórico de atendimento com lightbox para conferência rápida.
              </span>
            </li>
          </ul>
        </div>
        <div className="rounded-xl border border-gray-200 bg-gradient-to-br from-brand-50 to-white p-8 shadow-lg">
          <p className="text-sm font-medium uppercase tracking-wide text-brand-600">
            Photo-Lock ativo
          </p>
          <p className="mt-4 text-2xl font-bold text-gray-900">
            Pedido aguardando auditoria visual
          </p>
          <p className="mt-2 text-gray-600">
            Operador valida a imagem no painel antes do morador receber o Pix.
          </p>
          <div className="mt-6 aspect-video rounded-lg bg-gray-200 flex items-center justify-center text-gray-500 text-sm">
            [ Prévia da sacola — auditoria ]
          </div>
        </div>
      </div>
    </section>
  );
}

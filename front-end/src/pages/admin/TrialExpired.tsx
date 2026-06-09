import { Clock } from "lucide-react";
import { Link } from "react-router";
import PageMeta from "../../components/common/PageMeta";

const planPrice = import.meta.env.VITE_PLAN_PRICE?.trim() || "59,90";

export default function TrialExpired() {
  return (
    <div className="font-outfit flex min-h-screen flex-col items-center justify-center bg-gray-50 px-4 py-12">
      <PageMeta
        title="Trial encerrado | MarketChat"
        description="Ative sua assinatura para continuar usando o MarketChat."
        noIndex
      />
      <div className="mx-auto max-w-lg text-center">
        <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-brand-50 text-brand-600">
          <Clock className="h-8 w-8" aria-hidden />
        </div>
        <h1 className="mt-6 text-3xl font-bold text-gray-900">
          Seu período de teste de 7 dias chegou ao fim.
        </h1>
        <p className="mt-4 text-lg leading-relaxed text-gray-600">
          Para continuar monitorando seus mercados autônomos, mantendo seu robô do WhatsApp ativo
          e auditando as fotos de segurança dos moradores, ative sua assinatura do Plano Pro por
          apenas <strong className="text-gray-900">R$ {planPrice}/mês</strong> por mercado.
        </p>
        <Link
          to="/admin/settings?tab=plan"
          className="mt-8 inline-flex rounded-md bg-brand-500 px-8 py-3.5 text-base font-semibold text-white shadow-md transition-colors hover:bg-brand-600"
        >
          Ativar assinatura
        </Link>
      </div>
    </div>
  );
}

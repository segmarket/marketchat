import { Link } from "react-router";
import { useAuth } from "../../context/AuthContext";
import { formatDateTimeBR } from "../../features/settings/format";

export default function GracePeriodBanner() {
  const { user } = useAuth();

  if (!user?.is_in_grace_period) {
    return null;
  }

  const deadline = user.grace_ends_at ? ` até ${formatDateTimeBR(user.grace_ends_at)}` : "";

  return (
    <div className="shrink-0 border-b border-warning-200 bg-warning-50 px-4 py-2.5 text-center text-sm text-warning-900">
      <span>
        Aviso de cobrança: não conseguimos cobrar a mensalidade no seu cartão cadastrado. Pague a
        fatura em aberto{deadline} para evitar a suspensão do painel e dos atendimentos do WhatsApp.{" "}
      </span>
      <Link
        to="/admin/settings?tab=plan"
        className="font-semibold underline underline-offset-2 hover:text-warning-950"
      >
        Pagar fatura em Configurações
      </Link>
      <span>.</span>
    </div>
  );
}

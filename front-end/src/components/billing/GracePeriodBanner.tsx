import { Link } from "react-router";
import { useAuth } from "../../context/AuthContext";

export default function GracePeriodBanner() {
  const { user } = useAuth();

  if (!user?.is_in_grace_period) {
    return null;
  }

  return (
    <div className="shrink-0 border-b border-warning-200 bg-warning-50 px-4 py-2.5 text-center text-sm text-warning-900">
      <span>
        Aviso de cobrança: tivemos um problema ao processar a mensalidade no seu cartão cadastrado.
        Para evitar a suspensão dos atendimentos do WhatsApp nos seus condomínios nos próximos dias,{" "}
      </span>
      <Link
        to="/admin/settings?tab=plan"
        className="font-semibold underline underline-offset-2 hover:text-warning-950"
      >
        atualize seus dados de pagamento em Configurações
      </Link>
      <span>.</span>
    </div>
  );
}

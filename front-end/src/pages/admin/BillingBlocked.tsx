import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router";
import { AlertTriangle } from "lucide-react";
import PageMeta from "../../components/common/PageMeta";
import UpdateCardForm from "../../components/settings/UpdateCardForm";
import { useAuth } from "../../context/AuthContext";
import { fetchAccountSettings } from "../../features/settings/api";
import type { AccountSettingsResponse } from "../../features/settings/types";
import { getAxiosErrorMessage } from "../../utils/apiError";

export default function BillingBlocked() {
  const navigate = useNavigate();
  const { refreshUser } = useAuth();
  const [accountData, setAccountData] = useState<AccountSettingsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchAccountSettings();
      setAccountData(data);
    } catch (e: unknown) {
      setError(getAxiosErrorMessage(e));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  return (
    <div className="font-outfit flex min-h-screen flex-col items-center justify-center bg-gray-50 px-4 py-12">
      <PageMeta
        title="Acesso suspenso | MarketChat"
        description="Regularize o pagamento para reativar o MarketChat."
      />
      <div className="mx-auto w-full max-w-2xl">
        <div className="text-center">
          <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-error-50 text-error-600">
            <AlertTriangle className="h-8 w-8" aria-hidden />
          </div>
          <h1 className="mt-6 text-3xl font-bold text-gray-900">
            Acesso Suspenso por Pendência Financeira
          </h1>
          <p className="mt-4 text-lg leading-relaxed text-gray-600">
            Identificamos que a mensalidade do seu plano MarketChat está em atraso e o período de
            tolerância expirou. Para reativar seus dashboards e restabelecer os atendimentos dos
            robôs do WhatsApp nos seus mercados, atualize os dados do seu cartão abaixo.
          </p>
        </div>

        <div className="mt-10 rounded-2xl border border-gray-200 bg-white p-6 shadow-sm sm:p-8">
          {loading && <p className="text-center text-sm text-gray-500 animate-pulse">Carregando…</p>}
          {error && <p className="text-center text-sm text-error-600">{error}</p>}
          {accountData && !loading && (
            <UpdateCardForm
              accountData={accountData}
              submitLabel="Atualizar cartão e regularizar"
              onSuccess={async () => {
                await refreshUser();
                navigate("/admin", { replace: true });
              }}
            />
          )}
        </div>
      </div>
    </div>
  );
}

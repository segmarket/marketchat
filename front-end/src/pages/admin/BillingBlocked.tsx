import { useCallback, useEffect, useState } from "react";
import { Link, useNavigate } from "react-router";
import { AlertTriangle, Clock } from "lucide-react";
import PageMeta from "../../components/common/PageMeta";
import RequiredChargesNotice from "../../components/billing/RequiredChargesNotice";
import UpdateCardForm from "../../components/settings/UpdateCardForm";
import Button from "../../components/ui/button/Button";
import { useAuth } from "../../context/AuthContext";
import { fetchAccountSettings, fetchPaymentMethod } from "../../features/settings/api";
import type {
  AccountSettingsResponse,
  PaymentMethodSummary,
} from "../../features/settings/types";
import { getAxiosErrorMessage } from "../../utils/apiError";

const COPY = {
  trial_expired: {
    title: "Período de testes encerrado",
    body:
      "O período de testes terminou e a primeira mensalidade ainda não foi confirmada. " +
      "Para reativar os dashboards e os atendimentos do WhatsApp, pague a primeira fatura com um cartão de crédito.",
  },
  billing_overdue: {
    title: "Acesso suspenso por pendência financeira",
    body:
      "A mensalidade do seu plano MarketChat está em atraso e o prazo de carência terminou. " +
      "Para reativar os dashboards e os atendimentos do WhatsApp, pague a fatura em aberto com um cartão de crédito.",
  },
} as const;

export default function BillingBlocked() {
  const navigate = useNavigate();
  const { user, refreshUser } = useAuth();
  const [accountData, setAccountData] = useState<AccountSettingsResponse | null>(null);
  const [summary, setSummary] = useState<PaymentMethodSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [awaitingConfirmation, setAwaitingConfirmation] = useState(false);
  const [checking, setChecking] = useState(false);

  const reason = user?.billing_block_reason === "trial_expired" ? "trial_expired" : "billing_overdue";
  const copy = COPY[reason];

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [account, payment] = await Promise.all([
        fetchAccountSettings(),
        fetchPaymentMethod().catch(() => null),
      ]);
      setAccountData(account);
      setSummary(payment);
    } catch (e: unknown) {
      setError(getAxiosErrorMessage(e));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const goToPanelIfReleased = useCallback(async () => {
    setChecking(true);
    try {
      const fresh = await refreshUser();
      if (fresh && fresh.subscription_status !== "SUSPENDED" && !fresh.billing_blocked) {
        navigate("/admin", { replace: true });
        return true;
      }
      return false;
    } finally {
      setChecking(false);
    }
  }, [navigate, refreshUser]);

  return (
    <div className="font-outfit flex min-h-screen flex-col items-center justify-center bg-gray-50 px-4 py-12">
      <PageMeta
        title="Acesso suspenso | MarketChat"
        description="Pague a fatura em aberto para reativar o MarketChat."
        noIndex
      />
      <div className="mx-auto w-full max-w-2xl">
        <div className="text-center">
          <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-error-50 text-error-600">
            <AlertTriangle className="h-8 w-8" aria-hidden />
          </div>
          <h1 className="mt-6 text-3xl font-bold text-gray-900">{copy.title}</h1>
          <p className="mt-4 text-lg leading-relaxed text-gray-600">{copy.body}</p>
          <p className="mt-3 text-sm text-gray-500">
            O valor é cobrado na hora e o acesso volta assim que a operadora confirmar o pagamento.
            Apenas trocar o cartão, sem pagar a fatura, não libera o acesso.
          </p>
        </div>

        <div className="mt-10 rounded-2xl border border-gray-200 bg-white p-6 shadow-sm sm:p-8">
          {loading && <p className="text-center text-sm text-gray-500 animate-pulse">Carregando…</p>}
          {error && <p className="text-center text-sm text-error-600">{error}</p>}

          {awaitingConfirmation && (
            <div
              role="status"
              className="flex flex-col items-center gap-4 text-center"
            >
              <Clock className="h-8 w-8 text-warning-600" aria-hidden />
              <p className="text-sm text-gray-700">
                Pagamento enviado e aguardando confirmação da operadora. O acesso é liberado
                automaticamente quando ele for aprovado; não é preciso pagar de novo.
              </p>
              <Button
                variant="outline"
                disabled={checking}
                onClick={() => void goToPanelIfReleased()}
              >
                {checking ? "Verificando…" : "Verificar novamente"}
              </Button>
            </div>
          )}

          {accountData && !loading && !awaitingConfirmation && (
            <>
              <RequiredChargesNotice charges={summary?.required_charges ?? []} className="mb-6" />
              <UpdateCardForm
                accountData={accountData}
                mode="regularize"
                submitLabel="Pagar fatura e reativar"
                onRegularized={async (result) => {
                  if (result.status === "regularized") {
                    const released = await goToPanelIfReleased();
                    if (!released) setAwaitingConfirmation(true);
                    return;
                  }
                  setAwaitingConfirmation(true);
                }}
              />
            </>
          )}
        </div>

        <p className="mt-6 text-center text-sm text-gray-500">
          Após a reativação, se o WhatsApp tiver sido desconectado, reconecte-o lendo o QR Code em{" "}
          <Link
            to="/admin/settings?section=integrations"
            className="font-medium underline underline-offset-2"
          >
            Configurações › Integrações
          </Link>
          .
        </p>
      </div>
    </div>
  );
}

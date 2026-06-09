import { useCallback, useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router";
import { toast } from "sonner";
import AdminPageLayout from "../../components/layout/AdminPageShell";
import AccountSettingsForm from "../../components/settings/AccountSettingsForm";
import PlanPaymentPanel from "../../components/settings/PlanPaymentPanel";
import BillingHistoryTable from "../../components/settings/BillingHistoryTable";
import { fetchAccountSettings } from "../../features/settings/api";
import type { AccountSettingsResponse, SettingsSectionId } from "../../features/settings/types";
import { getAxiosErrorMessage } from "../../utils/apiError";
import MarketsPage from "./MarketsPage";
import IntegrationsPage from "./IntegrationsPage";
import PrivacyHub from "../../components/settings/PrivacyHub";

function resolveActiveSection(
  tab: string | null,
  section: string | null,
): SettingsSectionId {
  if (tab === "plan" || tab === "history") return tab;
  if (section === "markets" || section === "integrations" || section === "privacy") {
    return section;
  }
  return "account";
}

export default function SettingsPage() {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const [accountData, setAccountData] = useState<AccountSettingsResponse | null>(null);
  const [loading, setLoading] = useState(true);

  const activeSection = resolveActiveSection(
    searchParams.get("tab"),
    searchParams.get("section"),
  );

  const isTenantAdmin =
    accountData?.user.can_manage_integrations ?? accountData?.user.is_tenant_admin ?? false;
  const showIntegrations = Boolean(
    accountData?.user.can_manage_integrations ?? accountData?.user.is_tenant_admin,
  );

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await fetchAccountSettings();
      setAccountData(data);
    } catch (e: unknown) {
      toast.error(getAxiosErrorMessage(e));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    if (loading || !accountData) return;

    if (!isTenantAdmin && (activeSection === "plan" || activeSection === "history")) {
      setSearchParams({}, { replace: true });
    }
    if (!showIntegrations && activeSection === "integrations") {
      setSearchParams({}, { replace: true });
    }
    if (!isTenantAdmin && activeSection === "privacy") {
      setSearchParams({}, { replace: true });
    }
    if (searchParams.get("section") === "products") {
      navigate("/admin/products", { replace: true });
    }
  }, [
    loading,
    accountData,
    isTenantAdmin,
    showIntegrations,
    activeSection,
    searchParams,
    setSearchParams,
    navigate,
  ]);

  const sectionTitle: Record<SettingsSectionId, string> = {
    account: "Minha Conta",
    markets: "Mercados",
    integrations: "Integrações",
    privacy: "Privacidade",
    plan: "Plano e pagamento",
    history: "Histórico de Faturas",
  };

  const sectionDescriptions: Partial<Record<SettingsSectionId, string>> = {
    account: "Dados da conta e da empresa.",
    markets: "Cadastre e gerencie os mercados do seu condomínio.",
    integrations: "WhatsApp e conta Pix de recebimento.",
    privacy: "Exportação de dados e anonimização de moradores (LGPD).",
    plan: "Assinatura e forma de pagamento.",
    history: "Faturas e pagamentos anteriores.",
  };

  const pageTitle = `Configurações — ${sectionTitle[activeSection]}`;

  return (
    <AdminPageLayout
      pageTitle={pageTitle}
      metaTitle="Configurações | MarketChat"
      metaDescription="Conta, mercados e integrações."
      description={sectionDescriptions[activeSection]}
    >
      {loading || !accountData ? (
        <div className="space-y-4" aria-hidden>
          <div className="h-8 w-48 animate-pulse rounded bg-gray-100 dark:bg-white/10" />
          <div className="h-40 animate-pulse rounded-2xl border border-gray-200 bg-gray-50 dark:border-gray-800 dark:bg-white/5" />
          <div className="h-40 animate-pulse rounded-2xl border border-gray-200 bg-gray-50 dark:border-gray-800 dark:bg-white/5" />
        </div>
      ) : (
        <>
          {activeSection === "account" && (
            <AccountSettingsForm data={accountData} onUpdated={setAccountData} />
          )}
          {activeSection === "markets" && <MarketsPage embedded />}
          {activeSection === "integrations" && showIntegrations && (
            <IntegrationsPage embedded />
          )}
          {activeSection === "privacy" && isTenantAdmin && <PrivacyHub />}
          {activeSection === "plan" && isTenantAdmin && (
            <PlanPaymentPanel accountData={accountData} />
          )}
          {activeSection === "history" && isTenantAdmin && <BillingHistoryTable />}
        </>
      )}
    </AdminPageLayout>
  );
}

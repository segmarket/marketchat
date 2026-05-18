import { useCallback, useEffect, useState } from "react";
import { useSearchParams } from "react-router";
import { toast } from "sonner";
import PageBreadcrumb from "../../components/common/PageBreadCrumb";
import PageMeta from "../../components/common/PageMeta";
import FormPageLayout from "../../components/layout/FormPageLayout";
import SettingsTabs from "../../components/settings/SettingsTabs";
import AccountSettingsForm from "../../components/settings/AccountSettingsForm";
import PlanPaymentPanel from "../../components/settings/PlanPaymentPanel";
import BillingHistoryTable from "../../components/settings/BillingHistoryTable";
import { fetchAccountSettings } from "../../features/settings/api";
import type { AccountSettingsResponse, SettingsTabId } from "../../features/settings/types";
import { getAxiosErrorMessage } from "../../utils/apiError";

function tabFromParam(raw: string | null): SettingsTabId {
  if (raw === "plan" || raw === "history") return raw;
  return "account";
}

export default function SettingsPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [accountData, setAccountData] = useState<AccountSettingsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const activeTab = tabFromParam(searchParams.get("tab"));

  const isTenantAdmin =
    accountData?.user.can_manage_integrations ?? accountData?.user.is_tenant_admin ?? false;

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
    if (!isTenantAdmin && (activeTab === "plan" || activeTab === "history")) {
      setSearchParams({}, { replace: true });
    }
  }, [isTenantAdmin, activeTab, setSearchParams]);

  function handleTabChange(tab: SettingsTabId) {
    if (tab === "account") setSearchParams({});
    else setSearchParams({ tab });
  }

  return (
    <>
      <PageMeta title="Configurações | MarketChat" description="Conta, plano e faturas." />
      <FormPageLayout>
        <PageBreadcrumb pageTitle="Configurações" />

        {loading || !accountData ? (
          <p className="text-sm text-gray-500 animate-pulse dark:text-gray-400">Carregando configurações…</p>
        ) : (
          <div className="space-y-8">
            <div className="max-w-max rounded-lg border border-gray-200 bg-white p-0.5 shadow-theme-sm dark:border-gray-800 dark:bg-gray-900">
              <SettingsTabs activeTab={activeTab} onChange={handleTabChange} showBillingTabs={isTenantAdmin} />
            </div>

            {activeTab === "account" && (
              <AccountSettingsForm data={accountData} onUpdated={setAccountData} />
            )}
            {activeTab === "plan" && isTenantAdmin && <PlanPaymentPanel accountData={accountData} />}
            {activeTab === "history" && isTenantAdmin && <BillingHistoryTable />}
          </div>
        )}
      </FormPageLayout>
    </>
  );
}

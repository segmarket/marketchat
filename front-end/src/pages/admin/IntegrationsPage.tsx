import { useSearchParams } from "react-router";
import PageBreadcrumb from "../../components/common/PageBreadCrumb";
import PageMeta from "../../components/common/PageMeta";
import IntegrationsTabs from "../../components/integrations/IntegrationsTabs";
import PixConfigPanel from "../../components/integrations/pix/PixConfigPanel";
import type { IntegrationsTabId } from "../../features/integrations/types";
import WhatsAppConfig from "./WhatsAppConfig";

function tabFromParam(raw: string | null): IntegrationsTabId {
  if (raw === "pix") return "pix";
  return "whatsapp";
}

export default function IntegrationsPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const activeTab = tabFromParam(searchParams.get("tab"));

  function handleTabChange(tab: IntegrationsTabId) {
    if (tab === "whatsapp") {
      setSearchParams({});
    } else {
      setSearchParams({ tab });
    }
  }

  return (
    <>
      <PageMeta title="Integrações | MarketChat" description="WhatsApp e recebimentos Pix." />
      <PageBreadcrumb pageTitle="Integrações" />
      <IntegrationsTabs activeTab={activeTab} onChange={handleTabChange} />
      {activeTab === "whatsapp" ? <WhatsAppConfig embedded /> : <PixConfigPanel />}
    </>
  );
}

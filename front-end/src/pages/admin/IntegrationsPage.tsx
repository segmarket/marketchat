import { useSearchParams } from "react-router";
import PageBreadcrumb from "../../components/common/PageBreadCrumb";
import PageMeta from "../../components/common/PageMeta";
import IntegrationsTabs from "../../components/integrations/IntegrationsTabs";
import PixConfigPanel from "../../components/integrations/pix/PixConfigPanel";
import type { IntegrationsTabId } from "../../features/integrations/types";
import WhatsAppConfig from "./WhatsAppConfig";

function tabFromParam(raw: string | null, embedded: boolean): IntegrationsTabId {
  if (raw === "pix") return "pix";
  if (embedded && raw === "plan") return "whatsapp";
  return "whatsapp";
}

type Props = {
  embedded?: boolean;
};

export default function IntegrationsPage({ embedded = false }: Props) {
  const [searchParams, setSearchParams] = useSearchParams();
  const activeTab = tabFromParam(searchParams.get("tab"), embedded);

  function handleTabChange(tab: IntegrationsTabId) {
    if (embedded) {
      if (tab === "whatsapp") {
        setSearchParams({ section: "integrations" });
      } else {
        setSearchParams({ section: "integrations", tab: "pix" });
      }
      return;
    }
    if (tab === "whatsapp") {
      setSearchParams({});
    } else {
      setSearchParams({ tab });
    }
  }

  const content = (
    <>
      <IntegrationsTabs activeTab={activeTab} onChange={handleTabChange} />
      {activeTab === "whatsapp" ? <WhatsAppConfig embedded /> : <PixConfigPanel />}
    </>
  );

  if (embedded) {
    return content;
  }

  return (
    <>
      <PageMeta title="Integrações | MarketChat" description="WhatsApp e recebimentos Pix." />
      <PageBreadcrumb pageTitle="Integrações" />
      {content}
    </>
  );
}

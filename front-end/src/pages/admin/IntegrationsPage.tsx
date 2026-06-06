import PageBreadcrumb from "../../components/common/PageBreadCrumb";
import PageMeta from "../../components/common/PageMeta";
import PixReceivingAccountCard from "../../components/integrations/PixReceivingAccountCard";
import WhatsAppConfig from "./WhatsAppConfig";

type Props = {
  embedded?: boolean;
};

export default function IntegrationsPage({ embedded = false }: Props) {
  const content = (
    <div className="space-y-6">
      <WhatsAppConfig embedded />
      <PixReceivingAccountCard />
    </div>
  );

  if (embedded) {
    return content;
  }

  return (
    <>
      <PageMeta
        title="Integrações"
        description="Configure a conexão do WhatsApp com o MarketChat."
      />
      <PageBreadcrumb pageTitle="Integrações" />
      {content}
    </>
  );
}

/**
 * Landing pública — links para o painel usam `getAppUrl()` em `utils/host.ts`
 * (/signin, staging-app.marketchat.com.br, sem staging.app.*).
 */
import PageMeta from "../../components/common/PageMeta";
import MarketingFooter from "../../components/marketing/MarketingFooter";
import MarketingHero from "../../components/marketing/MarketingHero";
import MarketingNavbar from "../../components/marketing/MarketingNavbar";
import MarketingOwnerFlow from "../../components/marketing/MarketingOwnerFlow";
import MarketingPillarsGrid from "../../components/marketing/MarketingPillarsGrid";
import MarketingPricing from "../../components/marketing/MarketingPricing";

export default function LandingPage() {
  return (
    <div className="scroll-smooth font-outfit min-h-screen bg-white text-gray-900 antialiased">
      <PageMeta
        title="MarketChat | Gerente virtual para mercados autônomos"
        description="Ecossistema completo: vendas no WhatsApp, alertas de estoque e infraestrutura, Photo-Lock e painel operacional em tempo real para o dono do mercado."
      />
      <MarketingNavbar />
      <main>
        <MarketingHero />
        <MarketingPillarsGrid />
        <MarketingOwnerFlow />
        <MarketingPricing />
      </main>
      <MarketingFooter />
    </div>
  );
}

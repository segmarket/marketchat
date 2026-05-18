import PageMeta from "../../components/common/PageMeta";
import MarketingAdvantageGrid from "../../components/marketing/MarketingAdvantageGrid";
import MarketingFooter from "../../components/marketing/MarketingFooter";
import MarketingHero from "../../components/marketing/MarketingHero";
import MarketingJourney from "../../components/marketing/MarketingJourney";
import MarketingNavbar from "../../components/marketing/MarketingNavbar";
import MarketingPricing from "../../components/marketing/MarketingPricing";
import MarketingSecurity from "../../components/marketing/MarketingSecurity";

export default function LandingPage() {
  return (
    <div className="scroll-smooth font-outfit min-h-screen bg-white text-gray-900 antialiased">
      <PageMeta
        title="MarketChat | Mercado autônomo no WhatsApp do condomínio"
        description="Automatize vendas no mercado autônomo com IA no WhatsApp. Photo-Lock, Pix Asaas e painel operacional em um só lugar."
      />
      <MarketingNavbar />
      <main>
        <MarketingHero />
        <MarketingAdvantageGrid />
        <MarketingJourney />
        <MarketingSecurity />
        <MarketingPricing />
      </main>
      <MarketingFooter />
    </div>
  );
}

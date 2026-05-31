/**
 * Landing pública — links para o painel usam `getAppUrl()` em `utils/host.ts`
 * (/signin, staging-app.marketchat.com.br, sem staging.app.*).
 */
import { lazy, Suspense } from "react";
import PageMeta, { defaultSocialMeta } from "../../components/common/PageMeta";
import CookieConsentBanner from "../../components/marketing/CookieConsentBanner";
import MarketingAnalytics from "../../components/marketing/MarketingAnalytics";
import MarketingFooter from "../../components/marketing/MarketingFooter";
import MarketingHero from "../../components/marketing/MarketingHero";
import MarketingNavbar from "../../components/marketing/MarketingNavbar";
import MarketingStickyCtaBar from "../../components/marketing/MarketingStickyCtaBar";
import { useUTM } from "../../hooks/useUTM";

const MarketingPillarsGrid = lazy(() => import("../../components/marketing/MarketingPillarsGrid"));
const MarketingOwnerFlow = lazy(() => import("../../components/marketing/MarketingOwnerFlow"));
const MarketingPricing = lazy(() => import("../../components/marketing/MarketingPricing"));

export default function LandingPage() {
  useUTM();

  return (
    <div className="scroll-smooth font-outfit min-h-screen bg-white text-gray-900 antialiased">
      <PageMeta
        title={defaultSocialMeta.title}
        description={defaultSocialMeta.description}
        path="/"
      />
      <MarketingAnalytics />
      <MarketingNavbar />
      <main>
        <MarketingHero />
        <Suspense fallback={null}>
          <MarketingPillarsGrid />
          <MarketingOwnerFlow />
          <MarketingPricing />
        </Suspense>
      </main>
      <MarketingFooter />
      <MarketingStickyCtaBar />
      <CookieConsentBanner />
    </div>
  );
}

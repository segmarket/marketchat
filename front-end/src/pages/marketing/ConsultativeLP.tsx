/**
 * Landing consultiva — espelha a estrutura de LandingPage.tsx.
 * CTAs de trial/signup abrem o formulário F1 (modal) em vez de /auth/signup.
 */
import { lazy, Suspense, useState } from "react";
import PageMeta from "../../components/common/PageMeta";
import CookieConsentBanner from "../../components/marketing/CookieConsentBanner";
import MarketingFaq from "../../components/marketing/MarketingFaq";
import MarketingFooter from "../../components/marketing/MarketingFooter";
import MarketingHero from "../../components/marketing/MarketingHero";
import MarketingNavbar from "../../components/marketing/MarketingNavbar";
import MarketingStickyCtaBar from "../../components/marketing/MarketingStickyCtaBar";
import MarketingTrustBand from "../../components/marketing/MarketingTrustBand";
import { CONSULTATIVE_SUBTITLE } from "../../constants/marketingCopy";
import { ConsultativeLeadProvider } from "../../features/consultative/ConsultativeLeadContext";
import { useUTM } from "../../hooks/useUTM";

const MarketingPillarsGrid = lazy(() => import("../../components/marketing/MarketingPillarsGrid"));
const MarketingOwnerFlow = lazy(() => import("../../components/marketing/MarketingOwnerFlow"));
const InteractiveDemoSection = lazy(
  () => import("../../components/marketing/InteractiveDemoSection"),
);
const MarketingPricing = lazy(() => import("../../components/marketing/MarketingPricing"));

function ConsultativePageContent() {
  useUTM();
  const [cookieBannerHeight, setCookieBannerHeight] = useState(0);

  return (
    <div className="scroll-smooth font-outfit min-h-screen bg-white text-gray-900 antialiased">
      <PageMeta
        title="Consultoria — MarketChat"
        description={CONSULTATIVE_SUBTITLE}
        ogTitle="Consultoria gratuita — MarketChat"
        ogDescription={CONSULTATIVE_SUBTITLE}
        path="/consultoria"
      />
      <MarketingNavbar variant="consultative" />
      <main>
        <MarketingHero variant="consultative" />
        <MarketingTrustBand variant="consultative" />
        <Suspense fallback={null}>
          <MarketingPillarsGrid />
          <MarketingOwnerFlow />
          <InteractiveDemoSection />
          <MarketingPricing variant="consultative" />
          <MarketingFaq variant="consultative" />
        </Suspense>
      </main>
      <MarketingFooter variant="consultative" />
      <MarketingStickyCtaBar variant="consultative" bottomOffset={cookieBannerHeight} />
      <CookieConsentBanner onHeightChange={setCookieBannerHeight} />
    </div>
  );
}

export default function ConsultativeLP() {
  return (
    <ConsultativeLeadProvider>
      <ConsultativePageContent />
    </ConsultativeLeadProvider>
  );
}

/**
 * Landing pública — links para o painel usam `getAppUrl()` em `utils/host.ts`
 * (/signin, staging-app.marketchat.com.br, sem staging.app.*).
 */
import { lazy, Suspense, useState } from "react";
import PageMeta, { defaultSocialMeta } from "../../components/common/PageMeta";
import CookieConsentBanner from "../../components/marketing/CookieConsentBanner";
import MarketingFaq from "../../components/marketing/MarketingFaq";
import MarketingFooter from "../../components/marketing/MarketingFooter";
import MarketingHero from "../../components/marketing/MarketingHero";
import MarketingNavbar from "../../components/marketing/MarketingNavbar";
import MarketingStickyCtaBar from "../../components/marketing/MarketingStickyCtaBar";
import MarketingTrustBand from "../../components/marketing/MarketingTrustBand";
import { useUTM } from "../../hooks/useUTM";

const MarketingPillarsGrid = lazy(() => import("../../components/marketing/MarketingPillarsGrid"));
const MarketingOwnerFlow = lazy(() => import("../../components/marketing/MarketingOwnerFlow"));
const MarketingPricing = lazy(() => import("../../components/marketing/MarketingPricing"));

export default function LandingPage() {
  useUTM();
  const [cookieBannerHeight, setCookieBannerHeight] = useState(0);

  return (
    <div className="scroll-smooth font-outfit min-h-screen bg-white text-gray-900 antialiased">
      <PageMeta
        title={defaultSocialMeta.title}
        description={defaultSocialMeta.description}
        ogTitle={defaultSocialMeta.ogTitle}
        ogDescription={defaultSocialMeta.ogDescription}
        path="/"
      />
      <MarketingNavbar />
      <main>
        <MarketingHero />
        <MarketingTrustBand />
        <Suspense fallback={null}>
          <MarketingPillarsGrid />
          <MarketingOwnerFlow />
          <MarketingPricing />
          <MarketingFaq />
        </Suspense>
      </main>
      <MarketingFooter />
      <MarketingStickyCtaBar bottomOffset={cookieBannerHeight} />
      <CookieConsentBanner onHeightChange={setCookieBannerHeight} />
    </div>
  );
}

import { Check, Lock } from "lucide-react";
import ChatMockup from "./ChatMockup";
import DashboardMockup from "./DashboardMockup";
import { CTA_LOCATIONS } from "../../constants/analyticsEvents";
import MarketingCtaLink from "./MarketingCtaLink";
import {
  CTA_HOW_IT_WORKS,
  CTA_PRIMARY_LARGE_CLASS,
  CTA_SECONDARY_CLASS,
  CTA_TRIAL_PRIMARY,
  HERO_HEADLINE,
  HERO_MICROCOPY,
  HERO_SUBTITLE,
  MARKETING_BADGE,
} from "../../constants/marketingCopy";

export default function MarketingHero() {
  return (
    <section
      id="marketing-hero"
      className="relative overflow-hidden bg-gradient-to-b from-brand-25 to-white px-4 py-16 sm:px-6 sm:py-24 lg:px-8"
    >
      <div className="mx-auto grid max-w-7xl items-center gap-12 lg:grid-cols-2 lg:gap-16">
        <div>
          <p className="mb-4 inline-flex rounded-full bg-brand-50 px-3 py-1 text-sm font-medium text-brand-700 ring-1 ring-brand-200">
            {MARKETING_BADGE}
          </p>
          <h1 className="text-4xl font-bold leading-tight tracking-tight text-gray-900 sm:text-5xl lg:text-[3.25rem] lg:leading-[1.15]">
            {HERO_HEADLINE}
          </h1>
          <p className="mt-6 text-lg leading-relaxed text-gray-600">{HERO_SUBTITLE}</p>
          <div className="mt-8 flex flex-col gap-3 sm:flex-row sm:flex-wrap sm:items-center">
            <MarketingCtaLink
              className={CTA_PRIMARY_LARGE_CLASS}
              analyticsLocation={CTA_LOCATIONS.HERO}
            >
              {CTA_TRIAL_PRIMARY}
            </MarketingCtaLink>
            <a href="#para-o-dono" className={CTA_SECONDARY_CLASS}>
              {CTA_HOW_IT_WORKS}
            </a>
          </div>
          <p className="mt-4 flex flex-wrap items-center gap-x-3 gap-y-1 text-sm text-gray-600">
            <span className="inline-flex items-center gap-1.5">
              <Lock className="size-3.5 shrink-0 text-brand-500" aria-hidden />
              {HERO_MICROCOPY[0]}
            </span>
            <span aria-hidden>•</span>
            <span className="inline-flex items-center gap-1.5">
              <Check className="size-3.5 shrink-0 text-green-600" aria-hidden />
              {HERO_MICROCOPY[1]}
            </span>
            <span aria-hidden>•</span>
            <span>{HERO_MICROCOPY[2]}</span>
          </p>
        </div>

        <div className="relative flex items-center justify-center lg:justify-end">
          <div className="relative z-10 sm:-mr-12">
            <ChatMockup />
          </div>
          <div className="relative z-20 hidden translate-y-8 sm:block">
            <DashboardMockup />
          </div>
        </div>
      </div>
    </section>
  );
}

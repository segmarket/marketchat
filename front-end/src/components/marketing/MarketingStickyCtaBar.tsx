import { useEffect, useState } from "react";
import { CTA_LOCATIONS } from "../../constants/analyticsEvents";
import { CTA_TRIAL_PRIMARY } from "../../constants/marketingCopy";
import MarketingCtaLink from "./MarketingCtaLink";

type Props = {
  bottomOffset?: number;
};

export default function MarketingStickyCtaBar({ bottomOffset = 0 }: Props) {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const hero = document.getElementById("marketing-hero");
    if (!hero) {
      setVisible(false);
      return;
    }

    const observer = new IntersectionObserver(
      ([entry]) => {
        setVisible(!entry.isIntersecting);
      },
      { threshold: 0, rootMargin: "0px" },
    );

    observer.observe(hero);
    return () => observer.disconnect();
  }, []);

  if (!visible) {
    return null;
  }

  const offset = bottomOffset > 0 ? bottomOffset : 0;
  const cookieHeight =
    typeof document !== "undefined"
      ? document.documentElement.style.getPropertyValue("--cookie-banner-height")
      : "";
  const resolvedBottom = offset || (cookieHeight ? Number.parseInt(cookieHeight, 10) : 0);

  return (
    <div
      className="fixed inset-x-0 z-50 border-t border-brand-500/20 bg-white/95 p-3 shadow-[0_-4px_24px_rgba(0,0,0,0.08)] backdrop-blur-md md:hidden"
      style={{
        bottom: resolvedBottom,
        paddingBottom: "max(0.75rem, env(safe-area-inset-bottom))",
      }}
    >
      <MarketingCtaLink
        className="flex min-h-[48px] w-full items-center justify-center rounded-md bg-green-500 px-4 py-3.5 text-sm font-semibold text-white shadow-sm transition-colors hover:bg-green-600 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-green-600 focus-visible:ring-offset-2"
        analyticsLocation={CTA_LOCATIONS.STICKY_BAR}
      >
        {CTA_TRIAL_PRIMARY}
      </MarketingCtaLink>
    </div>
  );
}

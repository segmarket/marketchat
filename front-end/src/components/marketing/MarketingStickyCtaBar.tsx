import { useEffect, useState } from "react";
import MarketingCtaLink from "./MarketingCtaLink";

export default function MarketingStickyCtaBar() {
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

  return (
    <div className="fixed inset-x-0 bottom-0 z-50 border-t border-brand-500/20 bg-white/95 p-3 shadow-[0_-4px_24px_rgba(0,0,0,0.08)] backdrop-blur-md md:hidden pb-[max(0.75rem,env(safe-area-inset-bottom))]">
      <MarketingCtaLink className="flex w-full items-center justify-center rounded-md bg-green-500 px-4 py-3 text-sm font-semibold text-white shadow-sm transition-colors hover:bg-green-600">
        Começar 7 Dias Grátis
      </MarketingCtaLink>
    </div>
  );
}

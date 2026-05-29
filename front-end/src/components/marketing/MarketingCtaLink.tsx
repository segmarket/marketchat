import type { MouseEvent, ReactNode } from "react";
import {
  appendAttributionToUrl,
  loadAttribution,
} from "../../features/attribution/storage";
import { getAppUrl } from "../../utils/host";
import { pushToDataLayer } from "../../utils/analytics";

type MarketingCtaLinkProps = {
  children: ReactNode;
  className?: string;
  path?: string;
  trackEvent?: boolean;
};

export default function MarketingCtaLink({
  children,
  className = "",
  path = "/auth/signup",
  trackEvent = true,
}: MarketingCtaLinkProps) {
  const href = appendAttributionToUrl(getAppUrl(path));

  function handleClick(event: MouseEvent<HTMLAnchorElement>) {
    if (trackEvent) {
      pushToDataLayer("generate_lead", { ...loadAttribution() });
    }
    if (!event.metaKey && !event.ctrlKey && !event.shiftKey && event.button === 0) {
      // Navegação padrão via href; evento já disparado acima
    }
  }

  return (
    <a href={href} className={className} onClick={handleClick}>
      {children}
    </a>
  );
}

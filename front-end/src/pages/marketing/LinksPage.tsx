import { useEffect } from "react";
import PageMeta from "../../components/common/PageMeta";
import MarketchatLogo, { MARKETCHAT_LOGO_FOOTER_CLASS } from "../../components/brand/MarketchatLogo";
import CookieConsentBanner from "../../components/marketing/CookieConsentBanner";
import MarketingAnalytics from "../../components/marketing/MarketingAnalytics";
import MarketingCtaLink from "../../components/marketing/MarketingCtaLink";
import {
  LinksPageButtonExternal,
  LinksPageButtonLink,
  linksPrimaryClass,
} from "../../components/marketing/LinksPageButton";
import { InstagramIcon, WhatsAppIcon } from "../../components/marketing/MarketingSocialIcons";
import { INSTAGRAM_URL, WHATSAPP_SUPPORT_URL } from "../../constants/marketingUrls";
import { useUTM } from "../../hooks/useUTM";
import { pushToDataLayer } from "../../utils/analytics";

const SOCIAL_FOOTER_LINKS = [
  { label: "Instagram", href: INSTAGRAM_URL, icon: InstagramIcon },
  { label: "WhatsApp", href: WHATSAPP_SUPPORT_URL, icon: WhatsAppIcon },
] as const;

export default function LinksPage() {
  useUTM();

  useEffect(() => {
    pushToDataLayer("links_page_view");
  }, []);

  const year = new Date().getFullYear();

  return (
    <div className="flex min-h-screen flex-col bg-gray-950 font-outfit text-white antialiased">
      <PageMeta
        title="Links | MarketChat"
        description="Comece seu trial, conheça o MarketChat ou fale com nosso time. Links oficiais para redes sociais."
        path="/links"
      />
      <MarketingAnalytics />

      <main className="mx-auto flex w-full max-w-md flex-1 flex-col px-6 py-10">
        <header className="mb-10 flex flex-col items-center text-center">
          <MarketchatLogo
            variant="onDarkBackground"
            className={`${MARKETCHAT_LOGO_FOOTER_CLASS} mx-auto max-h-12`}
            loading="eager"
          />
          <p className="mt-4 text-sm text-slate-400">
            O gerente virtual do seu mercado autônomo
          </p>
        </header>

        <nav className="flex flex-col gap-4" aria-label="Links principais">
          <MarketingCtaLink className={linksPrimaryClass} path="/auth/signup">
            Começar 7 Dias Grátis
          </MarketingCtaLink>

          <LinksPageButtonLink to="/">Conheça o MarketChat</LinksPageButtonLink>

          <LinksPageButtonLink to="/signin">Painel do Cliente</LinksPageButtonLink>

          <LinksPageButtonExternal href={WHATSAPP_SUPPORT_URL}>
            <WhatsAppIcon className="h-5 w-5 shrink-0" aria-hidden />
            Falar com um Especialista
          </LinksPageButtonExternal>
        </nav>
      </main>

      <footer className="mt-auto border-t border-slate-800 px-6 py-8">
        <ul className="mx-auto flex max-w-md justify-center gap-4">
          {SOCIAL_FOOTER_LINKS.map(({ label, href, icon: Icon }) => (
            <li key={label}>
              <a
                href={href}
                target="_blank"
                rel="noopener noreferrer"
                aria-label={label}
                className="flex h-9 w-9 items-center justify-center rounded-lg border border-slate-700 bg-slate-900/80 text-slate-400 transition-colors hover:border-emerald-500/40 hover:text-white"
              >
                <Icon className="h-4 w-4 shrink-0" />
              </a>
            </li>
          ))}
        </ul>
        <p className="mt-4 text-center text-xs text-slate-500">
          © {year} MarketChat
        </p>
      </footer>

      <CookieConsentBanner />
    </div>
  );
}

import type { ComponentType, ReactNode, SVGProps } from "react";
import { ANALYTICS_EVENTS, CTA_LOCATIONS } from "../../constants/analyticsEvents";
import {
  COMPANY_ADDRESS_LINES,
  COMPANY_CNPJ,
  COMPANY_LEGAL_NAME,
  DPO_EMAIL,
  PRODUCT_NAME,
} from "../../constants/legalContent";
import { INSTAGRAM_URL, WHATSAPP_SUPPORT_PHONE_DISPLAY, WHATSAPP_SUPPORT_URL } from "../../constants/marketingUrls";
import { trackEvent } from "../../utils/analytics";
import { getAppUrl } from "../../utils/host";
import MarketchatLogo, { MARKETCHAT_LOGO_FOOTER_CLASS } from "../brand/MarketchatLogo";
import MarketingCtaLink from "./MarketingCtaLink";
import MarketingConsultativeCta from "./MarketingConsultativeCta";
import { InstagramIcon, WhatsAppIcon } from "./MarketingSocialIcons";

type SocialIcon = ComponentType<SVGProps<SVGSVGElement>>;

type SocialLink = {
  label: string;
  href: string;
  icon: SocialIcon;
};

const SOCIAL_LINKS: SocialLink[] = [
  { label: "WhatsApp", href: WHATSAPP_SUPPORT_URL, icon: WhatsAppIcon },
  { label: "Instagram", href: INSTAGRAM_URL, icon: InstagramIcon },
];

const NAV_LINKS = [
  { label: "Pilares", href: "#pilares" },
  { label: "Para o dono", href: "#para-o-dono" },
  { label: "Preços", href: "#precos" },
  { label: "FAQ", href: "#faq" },
  { label: "Privacidade", href: "/privacidade" },
  { label: "Termos de Uso", href: "/termos" },
] as const;

const CONSULTATIVE_FOOTER_LINKS = [
  { label: "Soluções", href: "#pilares" },
  { label: "Como funciona", href: "#para-o-dono" },
  { label: "Dúvidas", href: "#faq" },
  { label: "Privacidade", href: "/privacidade" },
  { label: "Termos de Uso", href: "/termos" },
] as const;


function FooterHeading({ children }: { children: ReactNode }) {
  return (
    <h3 className="text-xs font-bold uppercase tracking-wider text-brand-400">{children}</h3>
  );
}

function FooterLink({
  href,
  children,
  external,
  onClick,
}: {
  href: string;
  children: ReactNode;
  external?: boolean;
  onClick?: () => void;
}) {
  return (
    <a
      href={href}
      className="text-sm text-gray-300 transition-colors hover:text-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-400 rounded-sm"
      onClick={onClick}
      {...(external ? { target: "_blank", rel: "noopener noreferrer" } : {})}
    >
      {children}
    </a>
  );
}

function trackWhatsAppClick(location: string) {
  trackEvent(ANALYTICS_EVENTS.CLICK_WHATSAPP, { location });
}

export default function MarketingFooter({ variant = "default" }: { variant?: "default" | "consultative" }) {
  const year = new Date().getFullYear();
  const isConsultative = variant === "consultative";
  const navLinks = isConsultative ? CONSULTATIVE_FOOTER_LINKS : NAV_LINKS;

  const productLinks = [
    { label: "Acessar o sistema", href: getAppUrl() },
    {
      label: "Fale com nosso suporte",
      href: WHATSAPP_SUPPORT_URL,
      external: true,
      onClick: () => trackWhatsAppClick(CTA_LOCATIONS.FOOTER),
    },
  ] as const;

  return (
    <footer className="bg-gray-950 text-gray-400">
      <div className="mx-auto max-w-7xl px-4 py-14 sm:px-6 lg:px-8 lg:py-16">
        <div className="grid gap-10 sm:grid-cols-2 lg:grid-cols-12 lg:gap-8">
          {/* Marca + redes */}
          <div className="sm:col-span-2 lg:col-span-5">
            <MarketchatLogo
              variant="onDarkBackground"
              className={`${MARKETCHAT_LOGO_FOOTER_CLASS} max-h-10`}
              loading="lazy"
            />
            <p className="mt-5 max-w-md text-sm leading-relaxed text-gray-400">
              Ecossistema completo para mercados autônomos: vendas no WhatsApp, alertas de
              estoque e infraestrutura, Photo-Lock e painel operacional em tempo real para o
              dono do negócio.
            </p>
            <div className="mt-8">
              <FooterHeading>Acompanhe as novidades</FooterHeading>
              <ul className="mt-4 flex flex-wrap gap-3">
                {SOCIAL_LINKS.map(({ label, href, icon: Icon }) => (
                  <li key={label}>
                    <a
                      href={href}
                      target="_blank"
                      rel="noopener noreferrer"
                      aria-label={label}
                      className="flex h-10 w-10 items-center justify-center rounded-lg border border-gray-700 bg-gray-900 text-gray-300 transition-colors hover:border-brand-500 hover:bg-gray-800 hover:text-white"
                    >
                      <Icon className="h-5 w-5 shrink-0" />
                    </a>
                  </li>
                ))}
              </ul>
            </div>
          </div>

          {/* Navegação */}
          <div className="lg:col-span-2">
            <FooterHeading>Institucional</FooterHeading>
            <ul className="mt-4 space-y-3">
              {navLinks.map((link) => (
                <li key={link.href}>
                  <FooterLink href={link.href}>{link.label}</FooterLink>
                </li>
              ))}
            </ul>
          </div>

          {/* Produto */}
          <div className="lg:col-span-2">
            <FooterHeading>Produto</FooterHeading>
            <ul className="mt-4 space-y-3">
              {isConsultative ? (
                <li>
                  <MarketingConsultativeCta
                    className="text-sm text-gray-300 transition-colors hover:text-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-400 rounded-sm"
                    analyticsLocation={CTA_LOCATIONS.FOOTER}
                  >
                    Solicitar consultoria
                  </MarketingConsultativeCta>
                </li>
              ) : (
                <li>
                  <MarketingCtaLink
                    path="/auth/signup"
                    className="text-sm text-gray-300 transition-colors hover:text-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-400 rounded-sm"
                    analyticsLocation={CTA_LOCATIONS.FOOTER}
                  >
                    Começar 7 dias grátis
                  </MarketingCtaLink>
                </li>
              )}
              {productLinks.map((link) => (
                <li key={link.label}>
                  <FooterLink
                    href={link.href}
                    external={"external" in link && link.external}
                    onClick={"onClick" in link ? link.onClick : undefined}
                  >
                    {link.label}
                  </FooterLink>
                </li>
              ))}
            </ul>
          </div>

          {/* Contato e legal */}
          <div className="sm:col-span-2 lg:col-span-3">
            <FooterHeading>Contato</FooterHeading>
            <ul className="mt-4 space-y-3">
              <li>
                <FooterLink
                  href={WHATSAPP_SUPPORT_URL}
                  external
                  onClick={() => trackWhatsAppClick(CTA_LOCATIONS.FOOTER)}
                >
                  WhatsApp: {WHATSAPP_SUPPORT_PHONE_DISPLAY}
                </FooterLink>
              </li>
              <li>
                <FooterLink
                  href={WHATSAPP_SUPPORT_URL}
                  external
                  onClick={() => trackWhatsAppClick(CTA_LOCATIONS.FOOTER)}
                >
                  Fale com nosso suporte
                </FooterLink>
              </li>
            </ul>

            <div className="mt-8 space-y-6">
              <div>
                <FooterHeading>Endereço</FooterHeading>
                <address className="mt-3 text-sm not-italic leading-relaxed text-gray-400">
                  {COMPANY_ADDRESS_LINES.map((line, index) => (
                    <span key={line}>
                      {line}
                      {index < COMPANY_ADDRESS_LINES.length - 1 ? <br /> : null}
                    </span>
                  ))}
                </address>
              </div>
              <div>
                <FooterHeading>CNPJ</FooterHeading>
                <p className="mt-3 text-sm text-gray-300">{COMPANY_CNPJ}</p>
              </div>
              <div>
                <FooterHeading>Privacidade (DPO)</FooterHeading>
                <p className="mt-3 text-sm text-gray-300">
                  <FooterLink href={`mailto:${DPO_EMAIL}`} external>
                    {DPO_EMAIL}
                  </FooterLink>
                </p>
              </div>
            </div>
          </div>
        </div>

        <div className="mt-12 border-t border-gray-800 pt-8 text-center text-sm text-gray-500">
          <p>
            {year} | © {COMPANY_LEGAL_NAME} · {PRODUCT_NAME} | CNPJ {COMPANY_CNPJ} | Todos os Direitos Reservados.
          </p>
          <p className="mt-2">
            <FooterLink href="/privacidade">Política de Privacidade</FooterLink>
            <span className="mx-2 text-gray-600" aria-hidden>
              ·
            </span>
            <FooterLink href="/termos">Termos de Uso</FooterLink>
            <span className="mx-2 text-gray-600" aria-hidden>
              ·
            </span>
            <FooterLink href={`mailto:${DPO_EMAIL}`} external>
              {DPO_EMAIL}
            </FooterLink>
          </p>
        </div>
      </div>
    </footer>
  );
}

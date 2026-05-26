import type { ComponentType, ReactNode, SVGProps } from "react";
import { getAppUrl } from "../../utils/host";
import MarketingBrandLogo, { MARKETING_LOGO_FOOTER_CLASS } from "./MarketingBrandLogo";
import {
  FacebookIcon,
  InstagramIcon,
  LinkedInIcon,
  WhatsAppIcon,
  YouTubeIcon,
} from "./MarketingSocialIcons";

const WHATSAPP_SUPPORT_URL = "https://wa.me/5514991683639";

type SocialIcon = ComponentType<SVGProps<SVGSVGElement>>;

type SocialLink = {
  label: string;
  href: string;
  icon: SocialIcon;
};

function envSocialUrl(key: string): string | undefined {
  const value = import.meta.env[key]?.trim();
  return value || undefined;
}

/** URLs das redes — configure no .env; sem URL, o ícone abre o WhatsApp de suporte. */
const SOCIAL_LINKS: SocialLink[] = [
  { label: "WhatsApp", href: WHATSAPP_SUPPORT_URL, icon: WhatsAppIcon },
  {
    label: "Instagram",
    href: envSocialUrl("VITE_SOCIAL_INSTAGRAM") ?? WHATSAPP_SUPPORT_URL,
    icon: InstagramIcon,
  },
  {
    label: "Facebook",
    href: envSocialUrl("VITE_SOCIAL_FACEBOOK") ?? WHATSAPP_SUPPORT_URL,
    icon: FacebookIcon,
  },
  {
    label: "LinkedIn",
    href: envSocialUrl("VITE_SOCIAL_LINKEDIN") ?? WHATSAPP_SUPPORT_URL,
    icon: LinkedInIcon,
  },
  {
    label: "YouTube",
    href: envSocialUrl("VITE_SOCIAL_YOUTUBE") ?? WHATSAPP_SUPPORT_URL,
    icon: YouTubeIcon,
  },
];

const NAV_LINKS = [
  { label: "Pilares", href: "#pilares" },
  { label: "Para o dono", href: "#para-o-dono" },
  { label: "Preços", href: "#precos" },
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
}: {
  href: string;
  children: ReactNode;
  external?: boolean;
}) {
  return (
    <a
      href={href}
      className="text-sm text-gray-300 transition-colors hover:text-white"
      {...(external ? { target: "_blank", rel: "noopener noreferrer" } : {})}
    >
      {children}
    </a>
  );
}

export default function MarketingFooter() {
  const year = new Date().getFullYear();

  const productLinks = [
    { label: "Começar 7 dias grátis", href: getAppUrl("/signin") },
    { label: "Acessar o sistema", href: getAppUrl() },
    { label: "Fale com nosso suporte", href: WHATSAPP_SUPPORT_URL, external: true },
  ] as const;

  return (
    <footer className="bg-gray-950 text-gray-400">
      <div className="mx-auto max-w-7xl px-4 py-14 sm:px-6 lg:px-8 lg:py-16">
        <div className="grid gap-10 sm:grid-cols-2 lg:grid-cols-12 lg:gap-8">
          {/* Marca + redes */}
          <div className="sm:col-span-2 lg:col-span-5">
            <div className="inline-block rounded-xl bg-white px-4 py-3">
              <MarketingBrandLogo
                showWordmark={false}
                imageClassName={`${MARKETING_LOGO_FOOTER_CLASS} max-h-10`}
              />
            </div>
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
              {NAV_LINKS.map((link) => (
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
              {productLinks.map((link) => (
                <li key={link.label}>
                  <FooterLink href={link.href} external={"external" in link && link.external}>
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
                <FooterLink href={WHATSAPP_SUPPORT_URL} external>
                  WhatsApp: (14) 99168-3639
                </FooterLink>
              </li>
              <li>
                <FooterLink href={WHATSAPP_SUPPORT_URL} external>
                  Fale com nosso suporte
                </FooterLink>
              </li>
            </ul>

            <div className="mt-8 space-y-6">
              <div>
                <FooterHeading>Endereço</FooterHeading>
                <address className="mt-3 text-sm not-italic leading-relaxed text-gray-400">
                  Avenida Doutor Altino Arantes 131, Andar 13, Sala 136
                  <br />
                  Centro — Ourinhos, SP
                  <br />
                  CEP 19900-030
                </address>
              </div>
              <div>
                <FooterHeading>CNPJ</FooterHeading>
                <p className="mt-3 text-sm text-gray-300">35.960.300/0001-05</p>
              </div>
            </div>
          </div>
        </div>

        <div className="mt-12 border-t border-gray-800 pt-8">
          <p className="text-center text-sm text-gray-500">
            {year} | © Viva Software | Todos os Direitos Reservados.
          </p>
        </div>
      </div>
    </footer>
  );
}

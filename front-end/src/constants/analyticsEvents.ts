export const ANALYTICS_EVENTS = {
  CLICK_CTA_TRIAL: "click_cta_trial",
  CLICK_WHATSAPP: "click_whatsapp_contact",
  BEGIN_SIGNUP: "begin_signup",
  SIGN_UP: "sign_up",
  LOGIN: "login",
  REQUEST_WITHDRAWAL: "request_withdrawal",
  LINKS_PAGE_VIEW: "links_page_view",
} as const;

export const CTA_LOCATIONS = {
  HERO: "hero_section",
  STICKY_BAR: "sticky_bar",
  PRICING: "pricing",
  NAVBAR: "navbar",
  LINKS_BIO: "links_bio",
  FOOTER: "footer",
} as const;

export type CtaLocation = (typeof CTA_LOCATIONS)[keyof typeof CTA_LOCATIONS];

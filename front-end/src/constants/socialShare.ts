/** Textos e imagem padrão para preview em WhatsApp, LinkedIn, etc. (Open Graph). */
export const SOCIAL_SHARE_SITE_NAME = "MarketChat";

export const SOCIAL_SHARE_DEFAULT_TITLE =
  "MarketChat | Gerente virtual para mercados autônomos";

export const SOCIAL_SHARE_DEFAULT_DESCRIPTION =
  "Ecossistema completo: vendas no WhatsApp, alertas de estoque, Photo-Lock e painel operacional em tempo real para o dono do mercado autônomo.";

/** Caminho público (absoluto na origem marketing após build). */
export const SOCIAL_SHARE_DEFAULT_IMAGE_PATH = "/images/brand/og-marketchat-share.png";

/** ID do app Meta (Facebook) — meta fb:app_id no Sharing Debugger. */
export function getFacebookAppId(): string | undefined {
  const id = import.meta.env.VITE_FB_APP_ID?.trim();
  return id || undefined;
}

export function marketingOriginForShare(): string {
  const fromEnv = import.meta.env.VITE_MARKETING_ORIGIN?.trim();
  if (fromEnv) return fromEnv.replace(/\/$/, "");
  if (typeof window !== "undefined" && window.location?.origin) {
    return window.location.origin;
  }
  return "https://marketchat.com.br";
}

export function absoluteShareImageUrl(imagePath = SOCIAL_SHARE_DEFAULT_IMAGE_PATH): string {
  const path = imagePath.startsWith("/") ? imagePath : `/${imagePath}`;
  return `${marketingOriginForShare()}${path}`;
}

export function absoluteSharePageUrl(path = "/"): string {
  const normalized = path.startsWith("/") ? path : `/${path}`;
  return `${marketingOriginForShare()}${normalized}`;
}

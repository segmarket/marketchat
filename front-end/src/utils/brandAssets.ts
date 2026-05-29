/** Logotipo completo (mascote + nome) — use conforme o fundo ou o tema. */
export const LOGOTIPO_MARKETCHAT_COMPLETO_BRANCO =
  "/images/brand/logotipo_marketchat_completo_BRANCO.gif";

export const LOGOTIPO_MARKETCHAT_COMPLETO_PRETO =
  "/images/brand/logotipo_marketchat_completo_PRETO.gif";

export const LOGOTIPO_MARKETCHAT_MASCOTE_BRANCO =
  "/images/brand/logotipo_marketchat_mascote_BRANCO.gif";

export const LOGOTIPO_MARKETCHAT_MASCOTE_PRETO =
  "/images/brand/logotipo_marketchat_mascote_PRETO.gif";

/** Legado (PNG largo) — preferir os GIFs completos acima. */
export const LOGO_MARKETCHAT_PNG = "/images/brand/logo_marketchat.png";

export type MarketchatLogoVariant =
  | "theme"
  | "mascotTheme"
  | "onDarkBackground"
  | "onLightBackground";

export function getMarketchatLogoSrc(
  theme: "light" | "dark",
  variant: MarketchatLogoVariant = "theme",
): string {
  if (variant === "onDarkBackground") {
    return LOGOTIPO_MARKETCHAT_COMPLETO_BRANCO;
  }
  if (variant === "onLightBackground") {
    return LOGOTIPO_MARKETCHAT_COMPLETO_PRETO;
  }
  if (variant === "mascotTheme") {
    return theme === "dark"
      ? LOGOTIPO_MARKETCHAT_MASCOTE_BRANCO
      : LOGOTIPO_MARKETCHAT_MASCOTE_PRETO;
  }
  return theme === "dark"
    ? LOGOTIPO_MARKETCHAT_COMPLETO_BRANCO
    : LOGOTIPO_MARKETCHAT_COMPLETO_PRETO;
}

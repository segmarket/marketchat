import { useTheme } from "../../context/ThemeContext";
import {
  getMarketchatLogoSrc,
  type MarketchatLogoVariant,
} from "../../utils/brandAssets";

export const MARKETCHAT_LOGO_CLASS = "h-9 w-auto max-h-9 object-contain object-left";

export const MARKETCHAT_LOGO_FOOTER_CLASS = "h-8 w-auto max-h-8 object-contain object-left";

type MarketchatLogoProps = {
  className?: string;
  /** `theme`: branco no modo escuro, preto no modo claro. */
  variant?: MarketchatLogoVariant;
  loading?: "lazy" | "eager";
};

export default function MarketchatLogo({
  className = MARKETCHAT_LOGO_CLASS,
  variant = "theme",
  loading = "eager",
}: MarketchatLogoProps) {
  const { theme } = useTheme();
  const src = getMarketchatLogoSrc(theme, variant);

  return (
    <img
      src={src}
      alt="MarketChat"
      className={className}
      decoding="async"
      loading={loading}
      key={src}
    />
  );
}

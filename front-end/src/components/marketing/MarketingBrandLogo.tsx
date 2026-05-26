type MarketingBrandLogoProps = {
  className?: string;
  imageClassName?: string;
  showWordmark?: boolean;
};

export const MARKETING_LOGO_SRC = "/images/brand/logo_marketchat.png";

/** Altura padrão do logo na landing — só altura fixa; largura segue a proporção original. */
export const MARKETING_LOGO_CLASS = "h-9 w-auto max-h-9 object-contain object-left";

export const MARKETING_LOGO_FOOTER_CLASS = "h-8 w-auto max-h-8 object-contain object-left";

export default function MarketingBrandLogo({
  className = "",
  imageClassName = MARKETING_LOGO_CLASS,
  showWordmark = true,
}: MarketingBrandLogoProps) {
  return (
    <span className={`inline-flex items-center gap-2 ${className}`.trim()}>
      <img
        src={MARKETING_LOGO_SRC}
        alt="MarketChat"
        className={imageClassName}
        decoding="async"
      />
      {showWordmark ? (
        <span className="text-lg font-semibold text-gray-900">MarketChat</span>
      ) : null}
    </span>
  );
}

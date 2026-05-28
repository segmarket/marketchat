import MarketchatLogo, {
  MARKETCHAT_LOGO_CLASS,
  MARKETCHAT_LOGO_FOOTER_CLASS,
} from "../brand/MarketchatLogo";

export { MARKETCHAT_LOGO_CLASS as MARKETING_LOGO_CLASS };
export { MARKETCHAT_LOGO_FOOTER_CLASS as MARKETING_LOGO_FOOTER_CLASS };

type MarketingBrandLogoProps = {
  className?: string;
  imageClassName?: string;
  showWordmark?: boolean;
};

export default function MarketingBrandLogo({
  className = "",
  imageClassName = MARKETCHAT_LOGO_CLASS,
  showWordmark = true,
}: MarketingBrandLogoProps) {
  return (
    <span className={`inline-flex items-center gap-2 ${className}`.trim()}>
      <MarketchatLogo className={imageClassName} variant="theme" />
      {showWordmark ? (
        <span className="text-lg font-semibold text-gray-900 dark:text-white">MarketChat</span>
      ) : null}
    </span>
  );
}

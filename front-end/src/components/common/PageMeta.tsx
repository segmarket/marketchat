import { HelmetProvider, Helmet } from "react-helmet-async";
import {
  SOCIAL_SHARE_DEFAULT_DESCRIPTION,
  SOCIAL_SHARE_DEFAULT_IMAGE_PATH,
  SOCIAL_SHARE_DEFAULT_OG_DESCRIPTION,
  SOCIAL_SHARE_DEFAULT_TITLE,
  SOCIAL_SHARE_SITE_NAME,
  absoluteShareImageUrl,
  absoluteSharePageUrl,
  getFacebookAppId,
} from "../../constants/socialShare";

export type PageMetaProps = {
  title: string;
  description: string;
  /** Título Open Graph (padrão: `title`). */
  ogTitle?: string;
  /** Descrição Open Graph (padrão: `description`). */
  ogDescription?: string;
  /** Caminho da página para og:url (ex.: `/`, `/privacidade`). */
  path?: string;
  /** Caminho da imagem OG (padrão: og-marketchat.png). */
  imagePath?: string;
  /** Impede indexação (login, admin, etc.). */
  noIndex?: boolean;
};

const PageMeta = ({
  title,
  description,
  ogTitle,
  ogDescription,
  path = "/",
  imagePath = SOCIAL_SHARE_DEFAULT_IMAGE_PATH,
  noIndex = false,
}: PageMetaProps) => {
  const resolvedOgTitle = ogTitle ?? title;
  const resolvedOgDescription = ogDescription ?? description;
  const ogUrl = absoluteSharePageUrl(path);
  const ogImage = absoluteShareImageUrl(imagePath);
  const fbAppId = getFacebookAppId();

  return (
    <Helmet>
      <title>{title}</title>
      <meta name="description" content={description} />
      {noIndex ? <meta name="robots" content="noindex, nofollow" /> : null}
      <link rel="canonical" href={ogUrl} />

      <meta property="og:type" content="website" />
      <meta property="og:site_name" content={SOCIAL_SHARE_SITE_NAME} />
      <meta property="og:title" content={resolvedOgTitle} />
      <meta property="og:description" content={resolvedOgDescription} />
      <meta property="og:url" content={ogUrl} />
      <meta property="og:image" content={ogImage} />
      <meta property="og:image:secure_url" content={ogImage} />
      <meta property="og:image:width" content="1200" />
      <meta property="og:image:height" content="630" />
      <meta property="og:locale" content="pt_BR" />
      {fbAppId ? <meta property="fb:app_id" content={fbAppId} /> : null}

      <meta name="twitter:card" content="summary_large_image" />
      <meta name="twitter:title" content={resolvedOgTitle} />
      <meta name="twitter:description" content={resolvedOgDescription} />
      <meta name="twitter:image" content={ogImage} />
    </Helmet>
  );
};

/** Valores padrão da landing (também injetados no index.html para crawlers). */
export const defaultSocialMeta = {
  title: SOCIAL_SHARE_DEFAULT_TITLE,
  description: SOCIAL_SHARE_DEFAULT_DESCRIPTION,
  ogTitle: SOCIAL_SHARE_DEFAULT_TITLE,
  ogDescription: SOCIAL_SHARE_DEFAULT_OG_DESCRIPTION,
  imagePath: SOCIAL_SHARE_DEFAULT_IMAGE_PATH,
};

export const AppWrapper = ({ children }: { children: React.ReactNode }) => (
  <HelmetProvider>{children}</HelmetProvider>
);

export default PageMeta;

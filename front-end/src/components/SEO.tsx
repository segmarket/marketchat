import PageMeta from "./common/PageMeta";

export type SEOProps = {
  title: string;
  description: string;
  ogTitle?: string;
  ogDescription?: string;
  /** Caminho canônico relativo (ex.: `/`, `/links`). */
  canonicalUrl?: string;
  /** Caminho da imagem OG (ex.: `/images/brand/og-marketchat-share.png`). */
  ogImage?: string;
  noIndex?: boolean;
};

/** Wrapper público de SEO — delega para PageMeta (react-helmet-async). */
export default function SEO({
  title,
  description,
  ogTitle,
  ogDescription,
  canonicalUrl = "/",
  ogImage,
  noIndex = false,
}: SEOProps) {
  return (
    <PageMeta
      title={title}
      description={description}
      ogTitle={ogTitle}
      ogDescription={ogDescription}
      path={canonicalUrl}
      imagePath={ogImage}
      noIndex={noIndex}
    />
  );
}

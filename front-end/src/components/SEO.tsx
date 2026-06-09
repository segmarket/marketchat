import PageMeta from "./common/PageMeta";

export type SEOProps = {
  title: string;
  description: string;
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
  canonicalUrl = "/",
  ogImage,
  noIndex = false,
}: SEOProps) {
  return (
    <PageMeta
      title={title}
      description={description}
      path={canonicalUrl}
      imagePath={ogImage}
      noIndex={noIndex}
    />
  );
}

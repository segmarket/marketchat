# Preview de link no WhatsApp (Open Graph)

**Página de links (bio Instagram):** `https://marketchat.com.br/links` — rota pública em [`front-end/src/pages/marketing/LinksPage.tsx`](../front-end/src/pages/marketing/LinksPage.tsx).

O WhatsApp (e Facebook/LinkedIn) **não executam JavaScript**. Eles leem o HTML inicial de `index.html` após o build.

## O que o projeto faz

- Meta tags **Open Graph** e **Twitter Card** em `front-end/index.html` (placeholders substituídos no build).
- Plugin Vite `socialShareHtmlPlugin` usa `VITE_MARKETING_ORIGIN` para URLs absolutas (`og:url`, `og:image`).
- Imagem padrão: `front-end/public/images/brand/og-marketchat-share.png` (1200×630), gerada com mascote + nome brancos (sem zoom/recorte).
  Rode `python3 front-end/scripts/generate-og-image.py` após trocar a arte em `public/images/brand/`.
- Se o Facebook ainda mostrar a arte antiga: **Scrape Again** no depurador; a URL da imagem mudou de nome para invalidar cache.
- `PageMeta` (react-helmet) repete as tags para navegadores; crawlers usam o HTML estático.

## fb:app_id (Sharing Debugger)

O aviso *"fb:app_id ausente"* some quando você define o **ID do aplicativo Meta**:

1. [developers.facebook.com/apps](https://developers.facebook.com/apps/) → criar app (tipo **Negócios** ou **Outro**).
2. **Configurações do app → Básico** → copiar **ID do aplicativo** (só números).
3. Em `.env.production`:
   ```bash
   VITE_FB_APP_ID=1234567890123456
   ```
4. Rebuild do front e **Scrape Again** no depurador.

Sem esse ID o preview do WhatsApp ainda funciona; o aviso é recomendação do depurador da Meta.

## Deploy

1. `VITE_MARKETING_ORIGIN=https://marketchat.com.br` em `.env.production`.
2. `./scripts/producao/deploy-frontend.sh`
3. Confirme: `curl -sL https://marketchat.com.br/ | grep og:image`

## Atualizar cache do WhatsApp

Depois do deploy, force nova leitura:

- [Facebook Sharing Debugger](https://developers.facebook.com/tools/debug/) — URL `https://marketchat.com.br/`, botão **Scrape Again**.

O WhatsApp reutiliza o cache do Facebook.

## Personalizar

- Textos: `front-end/src/constants/socialShare.ts` e plugin em `vite.config.ts`.
- Arte: substitua `public/images/brand/og-marketchat.png` (recomendado 1200×630, PNG/JPG).

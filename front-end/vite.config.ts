import { defineConfig, loadEnv, type Plugin } from "vite";
import react from "@vitejs/plugin-react";
import svgr from "vite-plugin-svgr";

const DEFAULT_OG_TITLE = "MarketChat | Gerente virtual para mercados autônomos";
const DEFAULT_OG_DESCRIPTION =
  "Ecossistema completo: vendas no WhatsApp, alertas de estoque, Photo-Lock e painel operacional em tempo real para o dono do mercado autônomo.";
/** Nome novo quebra cache do Sharing Debugger (troque o sufixo ao atualizar a arte). */
const DEFAULT_OG_IMAGE_PATH = "/images/brand/og-marketchat-share.png";

function socialShareHtmlPlugin(marketingOrigin: string, fbAppId: string): Plugin {
  const origin = marketingOrigin.replace(/\/$/, "") || "https://marketchat.com.br";
  const ogUrl = `${origin}/`;
  const ogImage = `${origin}${DEFAULT_OG_IMAGE_PATH}`;
  const replacements: Record<string, string> = {
    __OG_TITLE__: DEFAULT_OG_TITLE,
    __OG_DESCRIPTION__: DEFAULT_OG_DESCRIPTION,
    __OG_URL__: ogUrl,
    __OG_IMAGE__: ogImage,
  };

  return {
    name: "marketchat-social-share-html",
    transformIndexHtml: {
      order: "pre",
      handler(html) {
        let out = html;
        for (const [token, value] of Object.entries(replacements)) {
          out = out.split(token).join(escapeHtmlAttr(value));
        }
        if (!fbAppId) {
          return out;
        }
        return {
          html: out,
          tags: [
            {
              tag: "meta",
              attrs: { property: "fb:app_id", content: fbAppId },
              injectTo: "head",
            },
          ],
        };
      },
    },
  };
}

function escapeHtmlAttr(value: string): string {
  return value
    .replace(/&/g, "&amp;")
    .replace(/"/g, "&quot;")
    .replace(/</g, "&lt;");
}

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  // 8000 costuma estar com Portainer; Django em dev usa 8001 (scripts/dev.sh).
  const apiPort = env.VITE_DEV_API_PORT?.trim() || "8001";
  const apiTarget = `http://127.0.0.1:${apiPort}`;
  const marketingOrigin =
    env.VITE_MARKETING_ORIGIN?.trim() || "https://marketchat.com.br";
  const fbAppId = env.VITE_FB_APP_ID?.trim() || "";

  return {
    server: {
      host: true,
      allowedHosts: ["localhost", "127.0.0.1", "app.localhost", "marketchat.localhost"],
      // Com `VITE_API_BASE_URL` vazio em dev, o axios usa URLs relativas (/api/...)
      // e o Vite encaminha para o Django (porta em VITE_DEV_API_PORT, padrão 8001).
      proxy: {
        "/api": {
          target: apiTarget,
          changeOrigin: true,
        },
      },
    },
    plugins: [
      socialShareHtmlPlugin(marketingOrigin, fbAppId),
      react(),
      svgr({
        svgrOptions: {
          icon: true,
          exportType: "named",
          namedExport: "ReactComponent",
        },
      }),
    ],
  };
});

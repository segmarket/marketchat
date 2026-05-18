import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";
import svgr from "vite-plugin-svgr";

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  // 8000 costuma estar com Portainer; Django em dev usa 8001 (scripts/dev.sh).
  const apiPort = env.VITE_DEV_API_PORT?.trim() || "8001";
  const apiTarget = `http://127.0.0.1:${apiPort}`;

  return {
    server: {
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

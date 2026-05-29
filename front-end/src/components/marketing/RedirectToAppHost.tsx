import { useEffect } from "react";
import { appendAttributionToUrl } from "../../features/attribution/storage";
import { getAppUrl } from "../../utils/host";

type Props = {
  /** Caminho no app (ex.: /reset-password, /signin). Query string da URL atual é preservada. */
  appPath: string;
};

/**
 * No host da landing (localhost / marketchat.com.br), rotas do painel não existem.
 * Redireciona para app.* mantendo ?uid=&token= etc.
 */
export default function RedirectToAppHost({ appPath }: Props) {
  useEffect(() => {
    const target = new URL(appendAttributionToUrl(getAppUrl(appPath)));
    if (window.location.search) {
      const incoming = new URLSearchParams(window.location.search);
      incoming.forEach((value, key) => {
        if (!target.searchParams.has(key)) {
          target.searchParams.set(key, value);
        }
      });
    }
    window.location.replace(target.toString());
  }, [appPath]);

  return (
    <p className="px-6 py-12 text-center text-sm text-gray-600">
      Redirecionando para o painel MarketChat…
    </p>
  );
}

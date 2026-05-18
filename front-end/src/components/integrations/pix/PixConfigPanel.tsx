import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";
import ComponentCard from "../../common/ComponentCard";
import { fetchPixConfig, savePixConfig } from "../../../features/integrations/pix/api";
import type { PixConfig } from "../../../features/integrations/pix/types";
import type { PixConfigFormValues } from "../../../features/integrations/pix/schemas";
import { getAxiosErrorMessage } from "../../../utils/apiError";
import PixAccountStatusCard from "./PixAccountStatusCard";
import PixConfigForm from "./PixConfigForm";
import PixInfoBanner from "./PixInfoBanner";

export default function PixConfigPanel() {
  const [config, setConfig] = useState<PixConfig | null>(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await fetchPixConfig();
      setConfig(data);
    } catch (err) {
      toast.error(
        getAxiosErrorMessage(err, { notAxiosMessage: "Não foi possível carregar as configurações Pix." }),
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  async function handleSubmit(values: PixConfigFormValues) {
    if (!config?.can_manage) {
      toast.error("Apenas administradores da empresa podem alterar as configurações Pix.");
      return;
    }
    setSubmitting(true);
    try {
      const updated = await savePixConfig(values);
      setConfig(updated);
      toast.success("Configurações Pix salvas com sucesso.");
    } catch (err) {
      toast.error(
        getAxiosErrorMessage(err, { notAxiosMessage: "Falha ao salvar configurações Pix." }),
      );
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <ComponentCard title="Configuração do PIX">
      {loading || !config ? (
        <p className="text-sm text-gray-500 animate-pulse dark:text-gray-400">Carregando…</p>
      ) : (
        <div className="space-y-6">
          <PixInfoBanner />

          {!config.can_manage && (
            <p className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-900 dark:border-amber-900/50 dark:bg-amber-950/40 dark:text-amber-100">
              Apenas administradores da empresa podem configurar o Pix de recebimento.
            </p>
          )}

          <div className="grid gap-6 lg:grid-cols-[1fr_240px]">
            <PixConfigForm
              config={config}
              disabled={!config.can_manage}
              submitting={submitting}
              onSubmit={(values) => void handleSubmit(values)}
            />
            <PixAccountStatusCard hasWallet={config.has_wallet} accountStatus={config.account_status} />
          </div>
        </div>
      )}
    </ComponentCard>
  );
}

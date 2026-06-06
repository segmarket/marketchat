import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";
import WalletPixKeyForm from "../financial/WalletPixKeyForm";
import Button from "../ui/button/Button";
import { fetchWalletSettings, updateWalletSettings } from "../../features/financial/api";
import { maskPixKeyDisplay } from "../../features/financial/maskPixKeyDisplay";
import { pixKeyTypeLabel } from "../../features/financial/pixKeyLabels";
import type { PixKeyType, WalletSettings } from "../../features/financial/types";
import { getAxiosErrorMessage } from "../../utils/apiError";

export default function PixReceivingAccountCard() {
  const [settings, setSettings] = useState<WalletSettings | null>(null);
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState(false);

  const loadSettings = useCallback(async () => {
    setLoading(true);
    try {
      const data = await fetchWalletSettings();
      setSettings(data);
      if (!data.has_pix_key_configured) {
        setEditing(true);
      }
    } catch (err) {
      toast.error(
        getAxiosErrorMessage(err, {
          notAxiosMessage: "Não foi possível carregar a conta Pix de recebimento.",
        }),
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadSettings();
  }, [loadSettings]);

  async function handleSubmit(values: { pixKeyType: PixKeyType; pixKey: string }) {
    try {
      const updated = await updateWalletSettings({
        default_pix_key_type: values.pixKeyType,
        default_pix_key: values.pixKey,
      });
      setSettings(updated);
      setEditing(false);
      toast.success("Conta de recebimento salva com sucesso.");
    } catch (err) {
      toast.error(
        getAxiosErrorMessage(err, { notAxiosMessage: "Não foi possível salvar a chave Pix." }),
      );
      throw err;
    }
  }

  if (loading) {
    return (
      <div className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm dark:border-gray-800 dark:bg-white/[0.03] md:p-6">
        <p className="animate-pulse text-sm text-gray-500 dark:text-gray-400">Carregando conta Pix…</p>
      </div>
    );
  }

  const configured = settings?.has_pix_key_configured ?? false;
  const keyType = (settings?.default_pix_key_type ?? "EMAIL") as PixKeyType;
  const maskedKey =
    settings?.default_pix_key_masked ||
    maskPixKeyDisplay(keyType, settings?.default_pix_key ?? "");

  return (
    <div className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm dark:border-gray-800 dark:bg-white/[0.03] md:p-6">
      <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-base font-semibold text-gray-900 dark:text-white/90">
            Conta de recebimento (Pix)
          </h2>
          <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
            Chave Pix onde os saques do painel financeiro serão enviados automaticamente.
          </p>
        </div>
        {configured && !editing ? (
          <Button type="button" variant="outline" size="sm" onClick={() => setEditing(true)}>
            Alterar
          </Button>
        ) : null}
      </div>

      {configured && !editing ? (
        <p className="text-sm text-gray-700 dark:text-gray-300">
          <span className="font-medium">Conta cadastrada:</span> {pixKeyTypeLabel(keyType)} —{" "}
          {maskedKey}
        </p>
      ) : (
        <WalletPixKeyForm
          initialType={keyType}
          initialKey=""
          submitLabel={configured ? "Salvar alteração" : "Salvar conta"}
          showCancel={configured}
          onCancel={() => setEditing(false)}
          onSubmit={handleSubmit}
        />
      )}
    </div>
  );
}

import { toast } from "sonner";
import { updateWalletSettings } from "../../features/financial/api";
import type { PixKeyType } from "../../features/financial/types";
import { getAxiosErrorMessage } from "../../utils/apiError";
import WalletPixKeyForm from "./WalletPixKeyForm";

type Props = {
  onSaved: () => void;
};

export default function WalletPixSettingsCard({ onSaved }: Props) {
  async function handleSubmit(values: { pixKeyType: PixKeyType; pixKey: string }) {
    try {
      await updateWalletSettings({
        default_pix_key_type: values.pixKeyType,
        default_pix_key: values.pixKey,
      });
      toast.success("Conta de recebimento salva com sucesso.");
      onSaved();
    } catch (err) {
      toast.error(
        getAxiosErrorMessage(err, { notAxiosMessage: "Não foi possível salvar a chave Pix." }),
      );
      throw err;
    }
  }

  return (
    <div className="mb-6 rounded-2xl border border-gray-200 bg-white p-5 shadow-sm dark:border-gray-800 dark:bg-white/[0.03] md:p-6">
      <div className="mb-4">
        <h2 className="text-base font-semibold text-gray-900 dark:text-white/90">
          Configurar conta de recebimento
        </h2>
        <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
          Cadastre a chave Pix onde você deseja receber os saques automaticamente.
        </p>
      </div>

      <WalletPixKeyForm submitLabel="Salvar conta" onSubmit={handleSubmit} />
    </div>
  );
}

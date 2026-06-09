import { useState } from "react";
import { IMaskInput } from "react-imask";
import { toast } from "sonner";
import Button from "../ui/button/Button";
import Label from "../form/Label";
import { anonymizeResidentByPhone, downloadTenantLgpdExport } from "../../features/lgpd/api";
import { getAxiosErrorMessage } from "../../utils/apiError";

export default function PrivacyHub() {
  const [exporting, setExporting] = useState(false);
  const [phone, setPhone] = useState("");
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [anonymizing, setAnonymizing] = useState(false);

  async function handleExport() {
    setExporting(true);
    try {
      await downloadTenantLgpdExport();
      toast.success("Exportação concluída.");
    } catch (e: unknown) {
      toast.error(getAxiosErrorMessage(e));
    } finally {
      setExporting(false);
    }
  }

  async function handleAnonymize() {
    setAnonymizing(true);
    try {
      const result = await anonymizeResidentByPhone(phone);
      toast.success(result.message);
      setPhone("");
      setConfirmOpen(false);
    } catch (e: unknown) {
      toast.error(getAxiosErrorMessage(e));
    } finally {
      setAnonymizing(false);
    }
  }

  return (
    <div className="space-y-8">
      <section className="rounded-2xl border border-gray-200 bg-white p-6 dark:border-gray-800 dark:bg-white/[0.03]">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Transparência e portabilidade</h2>
        <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">
          Baixe uma cópia dos dados cadastrais e financeiros da sua empresa em formato JSON,
          conforme o direito de portabilidade previsto na LGPD.
        </p>
        <Button type="button" className="mt-4" onClick={() => void handleExport()} disabled={exporting}>
          {exporting ? "Exportando…" : "Exportar meus dados (JSON)"}
        </Button>
      </section>

      <section className="rounded-2xl border border-gray-200 bg-white p-6 dark:border-gray-800 dark:bg-white/[0.03]">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Anonimizar morador</h2>
        <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">
          Quando um morador solicitar a exclusão dos dados pessoais, use esta ferramenta para anonimizar
          o cadastro. O histórico de vendas e o extrato financeiro são preservados para obrigações legais.
          Fotos de segurança (Photo-Lock) são removidas automaticamente após 30 dias.
        </p>
        <div className="mt-4 max-w-sm">
          <Label>Telefone do morador (WhatsApp)</Label>
          <IMaskInput
            mask="(00) 00000-0000"
            value={phone}
            onAccept={(value: string) => setPhone(value)}
            placeholder="(11) 99999-9999"
            className="mt-1 w-full rounded-lg border border-gray-300 bg-white px-4 py-2.5 text-sm text-gray-800 dark:border-gray-700 dark:bg-gray-900 dark:text-white"
          />
        </div>
        <Button
          type="button"
          variant="outline"
          className="mt-4"
          onClick={() => setConfirmOpen(true)}
          disabled={!phone.replace(/\D/g, "").length}
        >
          Anonimizar morador
        </Button>
      </section>

      {confirmOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
          <div className="w-full max-w-md rounded-2xl bg-white p-6 shadow-xl dark:bg-gray-900">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Confirmar anonimização</h3>
            <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">
              Esta ação é irreversível. Nome e telefone do morador serão anonimizados; mensagens de chat
              serão redigidas. Deseja continuar?
            </p>
            <div className="mt-6 flex justify-end gap-3">
              <Button type="button" variant="outline" onClick={() => setConfirmOpen(false)}>
                Cancelar
              </Button>
              <Button type="button" onClick={() => void handleAnonymize()} disabled={anonymizing}>
                {anonymizing ? "Processando…" : "Confirmar"}
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

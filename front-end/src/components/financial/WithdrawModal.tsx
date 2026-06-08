import { useEffect, useMemo, useState } from "react";
import { toast } from "sonner";
import { requestWithdraw } from "../../features/financial/api";
import { formatBRL } from "../../features/financial/format";
import { pixKeyTypeLabel } from "../../features/financial/pixKeyLabels";
import type { PixKeyType } from "../../features/financial/types";
import { getAxiosErrorMessage } from "../../utils/apiError";
import Button from "../ui/button/Button";
import Input from "../form/input/InputField";
import Label from "../form/Label";
import { Modal } from "../ui/modal";

type Props = {
  open: boolean;
  balanceAvailable: string;
  defaultPixKey: string;
  defaultPixKeyType: PixKeyType | "";
  onClose: () => void;
  onSuccess: () => void;
};

function parseAmount(raw: string): number {
  const normalized = raw.replace(/\./g, "").replace(",", ".").trim();
  const n = Number.parseFloat(normalized);
  return Number.isNaN(n) ? 0 : n;
}

export default function WithdrawModal({
  open,
  balanceAvailable,
  defaultPixKey,
  defaultPixKeyType,
  onClose,
  onSuccess,
}: Props) {
  const [amount, setAmount] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const maxBalance = useMemo(() => Number.parseFloat(balanceAvailable) || 0, [balanceAvailable]);
  const amountValue = parseAmount(amount);
  const amountError =
    amount && amountValue > maxBalance
      ? `O valor não pode ser maior que ${formatBRL(balanceAvailable)}.`
      : amount && amountValue <= 0
        ? "Informe um valor maior que zero."
        : "";

  useEffect(() => {
    if (!open) {
      setAmount("");
      setSubmitting(false);
    }
  }, [open]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (amountError || amountValue <= 0) return;

    setSubmitting(true);
    try {
      const response = await requestWithdraw({
        amount: amountValue.toFixed(2),
      });
      toast.success(response.message || "Saque solicitado com sucesso.");
      onSuccess();
      onClose();
    } catch (err) {
      toast.error(
        getAxiosErrorMessage(err, { notAxiosMessage: "Não foi possível solicitar o saque." }),
      );
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Modal isOpen={open} onClose={onClose} className="max-w-lg">
      <form onSubmit={handleSubmit} className="p-4 sm:p-6">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white/90">
          Solicitar saque via Pix
        </h2>
        <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
          Disponível: {formatBRL(balanceAvailable)}
        </p>

        <div className="mt-4 rounded-xl border border-gray-200 bg-gray-50 px-4 py-3 text-sm dark:border-gray-800 dark:bg-white/[0.03]">
          <p className="font-medium text-gray-800 dark:text-white/90">Conta de destino</p>
          <p className="mt-1 text-gray-600 dark:text-gray-400">
            {pixKeyTypeLabel(defaultPixKeyType)} — {defaultPixKey}
          </p>
        </div>

        <div className="mt-6">
          <Label>Qual valor deseja sacar?</Label>
          <Input
            type="text"
            placeholder="0,00"
            value={amount}
            onChange={(e) => setAmount(e.target.value)}
          />
          {amountError ? (
            <p className="mt-1 text-sm text-red-500">{amountError}</p>
          ) : null}
        </div>

        <div className="mt-6 flex flex-col-reverse gap-3 sm:flex-row sm:justify-end">
          <Button
            type="button"
            variant="outline"
            className="min-h-[44px]"
            onClick={onClose}
            disabled={submitting}
          >
            Cancelar
          </Button>
          <Button
            type="submit"
            className="min-h-[44px]"
            disabled={submitting || !!amountError || amountValue <= 0}
          >
            {submitting ? "Enviando…" : "Confirmar saque"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}

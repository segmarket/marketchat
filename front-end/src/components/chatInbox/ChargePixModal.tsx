import { useEffect, useMemo, useState } from "react";
import { Plus, Trash2 } from "lucide-react";
import { toast } from "sonner";
import {
  formatChatPixMessage,
  generateChatPix,
  type ChatPixItemInput,
} from "../../features/chatLogs/chatPix";
import { formatBRL } from "../../features/financial/format";
import { getAxiosErrorMessage } from "../../utils/apiError";
import Button from "../ui/button/Button";
import Input from "../form/input/InputField";
import Label from "../form/Label";
import { Modal } from "../ui/modal";
import ProductItemCombobox from "./ProductItemCombobox";

type Props = {
  open: boolean;
  sessionId: number;
  onClose: () => void;
  onInsertDraft: (text: string) => void;
};

type DraftItem = {
  key: string;
  name: string;
  quantity: string;
  unitPrice: string;
};

function newItem(): DraftItem {
  return {
    key: `${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
    name: "",
    quantity: "1",
    unitPrice: "",
  };
}

function parseMoney(raw: string): number {
  const normalized = raw.replace(/\./g, "").replace(",", ".").trim();
  const n = Number.parseFloat(normalized);
  return Number.isNaN(n) ? 0 : n;
}

function toApiMoney(raw: string): string {
  return parseMoney(raw).toFixed(2);
}

export default function ChargePixModal({
  open,
  sessionId,
  onClose,
  onInsertDraft,
}: Props) {
  const [amountOnly, setAmountOnly] = useState(false);
  const [amount, setAmount] = useState("");
  const [items, setItems] = useState<DraftItem[]>([newItem()]);
  const [description, setDescription] = useState("");
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (!open) {
      setAmountOnly(false);
      setAmount("");
      setItems([newItem()]);
      setDescription("");
      setSubmitting(false);
    }
  }, [open]);

  const total = useMemo(() => {
    if (amountOnly) return parseMoney(amount);
    return items.reduce((sum, item) => {
      const qty = Number.parseInt(item.quantity, 10) || 0;
      return sum + qty * parseMoney(item.unitPrice);
    }, 0);
  }, [amountOnly, amount, items]);

  function updateItem(key: string, patch: Partial<DraftItem>) {
    setItems((prev) => prev.map((row) => (row.key === key ? { ...row, ...patch } : row)));
  }

  function removeItem(key: string) {
    setItems((prev) => (prev.length <= 1 ? prev : prev.filter((row) => row.key !== key)));
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (total <= 0) {
      toast.error("Informe um valor total maior que zero.");
      return;
    }

    setSubmitting(true);
    try {
      let payloadItems: ChatPixItemInput[] | undefined;
      let payloadAmount: string | undefined;

      if (amountOnly) {
        payloadAmount = toApiMoney(amount);
      } else {
        const cleaned: ChatPixItemInput[] = [];
        for (const row of items) {
          const name = row.name.trim();
          const qty = Number.parseInt(row.quantity, 10);
          const unit = parseMoney(row.unitPrice);
          if (!name || !qty || qty <= 0 || unit <= 0) {
            toast.error("Preencha nome, quantidade e valor de cada item.");
            setSubmitting(false);
            return;
          }
          cleaned.push({
            name,
            quantity: qty,
            unit_price: unit.toFixed(2),
          });
        }
        payloadItems = cleaned;
      }

      const data = await generateChatPix({
        sessionId,
        items: payloadItems,
        amount: payloadAmount,
        description: description.trim() || undefined,
      });
      onInsertDraft(formatChatPixMessage(data));
      toast.success("Cobrança gerada. Revise a mensagem e envie.");
      onClose();
    } catch (err) {
      toast.error(
        getAxiosErrorMessage(err, {
          notAxiosMessage: "Não foi possível gerar a cobrança PIX.",
        }),
      );
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Modal isOpen={open} onClose={onClose} className="max-w-xl">
      <form onSubmit={(e) => void handleSubmit(e)} className="p-4 sm:p-6">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white/90">
          Gerar cobrança PIX
        </h2>
        <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
          Monte o pedido ou informe um valor avulso. O código PIX será inserido
          no campo de mensagem para você revisar.
        </p>

        <div className="mt-4 flex items-center gap-2">
          <input
            id="charge-amount-only"
            type="checkbox"
            checked={amountOnly}
            onChange={(e) => setAmountOnly(e.target.checked)}
            className="size-4 rounded border-gray-300 text-brand-500 focus:ring-brand-400"
          />
          <Label htmlFor="charge-amount-only" className="mb-0">
            Gerar apenas valor (cobrança avulsa)
          </Label>
        </div>

        {amountOnly ? (
          <div className="mt-4">
            <Label>Valor (R$)</Label>
            <Input
              type="text"
              placeholder="0,00"
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
            />
          </div>
        ) : (
          <div className="mt-4 space-y-3">
            {items.map((item) => (
              <div
                key={item.key}
                className="grid grid-cols-12 gap-2 rounded-xl border border-gray-200 p-3 dark:border-gray-800"
              >
                <div className="col-span-12 sm:col-span-5">
                  <Label>Item</Label>
                  <ProductItemCombobox
                    value={item.name}
                    onChange={(name) => updateItem(item.key, { name })}
                    onSelect={({ name, price }) =>
                      updateItem(item.key, { name, unitPrice: price })
                    }
                  />
                </div>
                <div className="col-span-4 sm:col-span-2">
                  <Label>Qtd</Label>
                  <Input
                    type="number"
                    min="1"
                    value={item.quantity}
                    onChange={(e) => updateItem(item.key, { quantity: e.target.value })}
                  />
                </div>
                <div className="col-span-6 sm:col-span-4">
                  <Label>Valor unitário</Label>
                  <Input
                    type="text"
                    placeholder="0,00"
                    value={item.unitPrice}
                    onChange={(e) => updateItem(item.key, { unitPrice: e.target.value })}
                  />
                </div>
                <div className="col-span-2 flex items-end sm:col-span-1">
                  <button
                    type="button"
                    onClick={() => removeItem(item.key)}
                    disabled={items.length <= 1}
                    className="inline-flex h-11 w-full items-center justify-center rounded-xl text-gray-500 hover:bg-gray-100 disabled:opacity-40 dark:hover:bg-white/10"
                    aria-label="Remover item"
                  >
                    <Trash2 className="size-4" />
                  </button>
                </div>
              </div>
            ))}
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => setItems((prev) => [...prev, newItem()])}
            >
              <Plus className="mr-1 size-4" />
              Adicionar item
            </Button>
          </div>
        )}

        <div className="mt-4">
          <Label>Descrição (opcional)</Label>
          <Input
            type="text"
            placeholder="Ex.: Pedido balcão"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
          />
        </div>

        <p className="mt-4 text-sm font-semibold text-gray-800 dark:text-white/90">
          Valor total: {formatBRL(total)}
        </p>

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
            disabled={submitting || total <= 0}
          >
            {submitting ? "Gerando…" : "Gerar cobrança e inserir no chat"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}

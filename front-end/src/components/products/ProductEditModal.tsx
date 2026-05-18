import { useEffect, useState } from "react";
import { toast } from "sonner";
import Label from "../form/Label";
import Input from "../form/input/InputField";
import TextArea from "../form/input/TextArea";
import { Modal } from "../ui/modal";
import Button from "../ui/button/Button";
import { patchProduct } from "../../features/products/api";
import type { Product, ProductStatus } from "../../features/products/types";
import { getAxiosErrorMessage } from "../../utils/apiError";

type Props = {
  product: Product | null;
  isOpen: boolean;
  onClose: () => void;
  onSaved: (product: Product) => void;
};

export default function ProductEditModal({ product, isOpen, onClose, onSaved }: Props) {
  const [name, setName] = useState("");
  const [searchAliases, setSearchAliases] = useState("");
  const [price, setPrice] = useState("");
  const [status, setStatus] = useState<ProductStatus>("active");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!product) return;
    setName(product.name);
    setSearchAliases(product.search_aliases ?? "");
    setPrice(product.price);
    setStatus(product.status);
  }, [product]);

  async function handleSave() {
    if (!product) return;
    const trimmedName = name.trim();
    if (!trimmedName) {
      toast.error("Informe o nome do produto.");
      return;
    }
    const priceNum = Number.parseFloat(price.replace(",", "."));
    if (Number.isNaN(priceNum) || priceNum < 0) {
      toast.error("Informe um preço válido.");
      return;
    }

    setBusy(true);
    try {
      const updated = await patchProduct(product.id, {
        name: trimmedName,
        search_aliases: searchAliases.trim(),
        price: priceNum.toFixed(2),
        status,
      });
      toast.success("Produto atualizado.");
      onSaved(updated);
      onClose();
    } catch (err) {
      toast.error(getAxiosErrorMessage(err, { notAxiosMessage: "Falha ao salvar produto." }));
    } finally {
      setBusy(false);
    }
  }

  return (
    <Modal isOpen={isOpen} onClose={onClose} className="max-w-md p-6">
      <h3 className="text-lg font-semibold text-gray-900 dark:text-white/90">Editar produto</h3>
      {product && (
        <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">SKU: {product.sku}</p>
      )}
      <div className="mt-5 space-y-4">
        <div>
          <Label>Nome</Label>
          <Input value={name} onChange={(e) => setName(e.target.value)} />
        </div>
        <div>
          <Label>Sinônimos de busca</Label>
          <TextArea
            rows={3}
            placeholder="coca, refrigerante, cola"
            value={searchAliases}
            onChange={setSearchAliases}
          />
          <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
            Separe por vírgula ou quebra de linha. Usado pelo robô para encontrar o produto.
          </p>
        </div>
        <div>
          <Label>Preço</Label>
          <Input
            type="number"
            min="0"
            step={0.01}
            value={price}
            onChange={(e) => setPrice(e.target.value)}
          />
        </div>
        <div>
          <Label>Status</Label>
          <select
            value={status}
            onChange={(e) => setStatus(e.target.value as ProductStatus)}
            className="h-11 w-full rounded-lg border border-gray-300 bg-transparent px-4 py-2.5 text-sm text-gray-800 shadow-theme-xs focus:border-brand-300 focus:outline-hidden focus:ring-3 focus:ring-brand-500/10 dark:border-gray-700 dark:bg-gray-900 dark:text-white/90"
          >
            <option value="active">Ativo</option>
            <option value="inactive">Inativo</option>
          </select>
        </div>
      </div>
      <div className="mt-6 flex flex-wrap justify-end gap-3">
        <Button variant="outline" onClick={onClose} disabled={busy}>
          Cancelar
        </Button>
        <Button onClick={() => void handleSave()} disabled={busy}>
          {busy ? "Salvando…" : "Salvar"}
        </Button>
      </div>
    </Modal>
  );
}

import { useEffect, useState } from "react";
import { Search, X } from "lucide-react";
import { fetchCartSecurityPhoto } from "../../features/sales/api";
import {
  formatBRL,
  formatOrderDateTime,
} from "../../features/sales/format";
import type { CartDetail } from "../../features/sales/types";
import CartStatusBadge from "./CartStatusBadge";
import { Table, TableBody, TableCell, TableHeader, TableRow } from "../ui/table";

type Props = {
  open: boolean;
  loading: boolean;
  cart: CartDetail | null;
  onClose: () => void;
};

export default function OrderDetailsModal({ open, loading, cart, onClose }: Props) {
  const [isImageExpanded, setIsImageExpanded] = useState(false);
  const [photoSrc, setPhotoSrc] = useState<string | null>(null);
  const [photoLoading, setPhotoLoading] = useState(false);

  useEffect(() => {
    setIsImageExpanded(false);
  }, [open, cart?.id]);

  useEffect(() => {
    if (!open || !cart?.security_photo_url) {
      setPhotoSrc(null);
      return;
    }

    let cancelled = false;
    let objectUrl: string | null = null;
    setPhotoLoading(true);

    fetchCartSecurityPhoto(cart.id)
      .then((blob) => {
        if (cancelled) return;
        objectUrl = URL.createObjectURL(blob);
        setPhotoSrc(objectUrl);
      })
      .catch(() => {
        if (!cancelled) setPhotoSrc(null);
      })
      .finally(() => {
        if (!cancelled) setPhotoLoading(false);
      });

    return () => {
      cancelled = true;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
      setPhotoSrc(null);
    };
  }, [open, cart?.id, cart?.security_photo_url]);

  useEffect(() => {
    if (!open) return;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = "unset";
    };
  }, [open]);

  useEffect(() => {
    if (!open) return;
    function onKey(e: KeyboardEvent) {
      if (e.key !== "Escape") return;
      if (isImageExpanded) {
        setIsImageExpanded(false);
        return;
      }
      onClose();
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose, isImageExpanded]);

  if (!open) return null;

  const hasPhoto = Boolean(cart?.security_photo_url);

  return (
    <div className="fixed inset-0 z-[99999] flex items-center justify-center p-3 sm:p-4">
      <button
        type="button"
        aria-label="Fechar detalhes"
        className="absolute inset-0 bg-black/60 backdrop-blur-sm"
        onClick={onClose}
      />
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="order-details-title"
        className="relative z-10 flex max-h-[min(92vh,900px)] w-[95%] max-w-4xl flex-col overflow-hidden rounded-xl border border-gray-200 bg-white shadow-2xl dark:border-gray-800 dark:bg-gray-900 md:w-full"
        onClick={(e) => e.stopPropagation()}
      >
        <header className="flex shrink-0 items-center justify-between gap-3 border-b border-gray-200 px-5 py-4 dark:border-gray-800">
          <div className="flex min-w-0 flex-wrap items-center gap-2 sm:gap-3">
            <h2
              id="order-details-title"
              className="text-lg font-semibold text-gray-800 dark:text-white/90"
            >
              Detalhes do Pedido #{cart?.id ?? "—"}
            </h2>
            {cart ? <CartStatusBadge status={cart.status} /> : null}
          </div>
          <button
            type="button"
            aria-label="Fechar"
            onClick={onClose}
            className="shrink-0 rounded-lg p-1.5 text-gray-500 transition-colors hover:bg-gray-100 dark:hover:bg-white/10"
          >
            <X className="size-5" />
          </button>
        </header>

        <div className="flex-1 overflow-y-auto px-5 py-4">
          {loading ? (
            <p className="text-sm text-gray-500">Carregando detalhes…</p>
          ) : cart ? (
            <div className="grid gap-6 lg:grid-cols-5">
              <div className="space-y-6 lg:col-span-3">
                <section className="grid gap-3 sm:grid-cols-2">
                  <DataField label="Morador" value={cart.resident_name || "—"} />
                  <DataField label="Condomínio" value={cart.market_name || "—"} />
                  <DataField label="Data/Hora" value={formatOrderDateTime(cart.created_at)} />
                  <DataField
                    label="ID da cobrança"
                    value={cart.asaas_billing_id || "—"}
                    mono={Boolean(cart.asaas_billing_id)}
                  />
                </section>

                <section>
                  <h3 className="mb-2 text-sm font-semibold text-gray-800 dark:text-white/90">
                    Itens do pedido
                  </h3>
                  <div className="overflow-x-auto rounded-lg border border-gray-200 dark:border-gray-800">
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableCell isHeader className="px-3 py-2 text-xs text-gray-500">
                            Produto
                          </TableCell>
                          <TableCell isHeader className="px-3 py-2 text-xs text-gray-500">
                            Qtd
                          </TableCell>
                          <TableCell isHeader className="px-3 py-2 text-xs text-gray-500">
                            Preço Un.
                          </TableCell>
                          <TableCell isHeader className="px-3 py-2 text-xs text-gray-500">
                            Subtotal
                          </TableCell>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {cart.items.map((item) => (
                          <TableRow key={`${item.sku}-${item.product_name}`}>
                            <TableCell className="px-3 py-2 text-sm">
                              <div className="flex items-center gap-2">
                                <div className="flex size-8 shrink-0 items-center justify-center rounded bg-gray-100 text-[10px] text-gray-500 dark:bg-gray-800">
                                  {item.sku.slice(0, 3)}
                                </div>
                                <span>{item.product_name}</span>
                              </div>
                            </TableCell>
                            <TableCell className="px-3 py-2 text-sm">{item.quantity}</TableCell>
                            <TableCell className="px-3 py-2 text-sm">
                              {formatBRL(item.unit_price)}
                            </TableCell>
                            <TableCell className="px-3 py-2 text-sm font-medium">
                              {formatBRL(item.subtotal)}
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                      <tfoot>
                        <tr>
                          <td
                            colSpan={4}
                            className="border-t border-gray-200 px-3 py-3 text-right text-sm font-bold text-gray-800 dark:border-gray-800 dark:text-white/90"
                          >
                            Total: {formatBRL(cart.total_value)}
                          </td>
                        </tr>
                      </tfoot>
                    </Table>
                  </div>
                </section>
              </div>

              <aside className="lg:col-span-2">
                <section className="rounded-xl border border-gray-200 bg-gray-50/80 p-4 dark:border-gray-800 dark:bg-gray-900/50">
                  <h3 className="mb-3 text-sm font-semibold text-gray-800 dark:text-white/90">
                    Foto de Segurança
                  </h3>
                  {hasPhoto ? (
                    <button
                      type="button"
                      onClick={() => photoSrc && setIsImageExpanded(true)}
                      disabled={!photoSrc}
                      className="group relative block w-full overflow-hidden rounded-lg focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-500 disabled:cursor-wait"
                    >
                      <div className="aspect-[4/3] w-full overflow-hidden">
                        {photoLoading ? (
                          <div className="flex size-full items-center justify-center bg-gray-200 text-sm text-gray-500 dark:bg-gray-800">
                            Carregando foto…
                          </div>
                        ) : photoSrc ? (
                          <img
                            src={photoSrc}
                            alt="Foto de segurança enviada pelo morador"
                            className="size-full object-cover transition-transform duration-200 group-hover:scale-105"
                          />
                        ) : (
                          <div className="flex size-full items-center justify-center bg-gray-200 text-sm text-gray-500 dark:bg-gray-800">
                            Não foi possível carregar a foto.
                          </div>
                        )}
                      </div>
                      <div className="absolute inset-0 flex flex-col items-center justify-center gap-1 bg-black/35 transition-colors group-hover:bg-black/45">
                        <Search className="size-6 text-white" strokeWidth={2} />
                        <span className="text-xs text-white/90">Clique para ampliar</span>
                      </div>
                    </button>
                  ) : (
                    <p className="text-sm text-gray-500">
                      Nenhuma foto registrada. Disponível apenas para checkout com foto enviada
                      (aguardando pagamento ou concluído).
                    </p>
                  )}
                </section>
              </aside>
            </div>
          ) : (
            <p className="text-sm text-gray-500">Selecione um pedido na tabela.</p>
          )}
        </div>
      </div>

      {isImageExpanded && photoSrc ? (
        <div
          role="dialog"
          aria-modal="true"
          aria-label="Foto de segurança ampliada"
          className="fixed inset-0 z-[100000] flex items-center justify-center p-4"
        >
          <button
            type="button"
            aria-label="Fechar visualização"
            className="absolute inset-0 bg-black/90"
            onClick={() => setIsImageExpanded(false)}
          />
          <button
            type="button"
            aria-label="Fechar"
            onClick={() => setIsImageExpanded(false)}
            className="absolute right-4 top-4 z-10 rounded-full bg-white/10 p-2 text-white transition-colors hover:bg-white/20"
          >
            <X className="size-6" />
          </button>
          <img
            src={photoSrc}
            alt="Foto de segurança ampliada"
            className="relative z-10 max-h-[90vh] max-w-[95vw] object-contain"
            onClick={(e) => e.stopPropagation()}
          />
        </div>
      ) : null}
    </div>
  );
}

function DataField({
  label,
  value,
  mono = false,
}: {
  label: string;
  value: string;
  mono?: boolean;
}) {
  return (
    <div>
      <p className="text-xs uppercase tracking-wide text-gray-500 dark:text-gray-400">{label}</p>
      <p
        className={`mt-0.5 text-sm text-gray-800 dark:text-white/90 ${mono ? "font-mono text-xs" : ""}`}
      >
        {value}
      </p>
    </div>
  );
}

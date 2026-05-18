import { useEffect } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import Label from "../form/Label";
import { Modal } from "../ui/modal";
import Button from "../ui/button/Button";
import { formatPhoneBR } from "../../features/residents/format";
import {
  residentEditSchema,
  type ResidentEditFormValues,
} from "../../features/residents/schemas";
import type { Resident, ResidentMarketOption } from "../../features/residents/types";

type Props = {
  resident: Resident | null;
  markets: ResidentMarketOption[];
  isOpen: boolean;
  busy: boolean;
  onClose: () => void;
  onSubmit: (values: ResidentEditFormValues) => void;
};

export default function ResidentEditModal({
  resident,
  markets,
  isOpen,
  busy,
  onClose,
  onSubmit,
}: Props) {
  const { register, handleSubmit, reset, formState: { errors } } = useForm<ResidentEditFormValues>({
    resolver: zodResolver(residentEditSchema),
    defaultValues: { market_id: String(resident?.market?.id ?? markets[0]?.id ?? "") },
  });

  useEffect(() => {
    if (resident && isOpen) {
      reset({ market_id: String(resident.market?.id ?? markets[0]?.id ?? "") });
    }
  }, [resident, markets, isOpen, reset]);

  return (
    <Modal isOpen={isOpen} onClose={onClose} className="max-w-md p-6">
      <h3 className="text-lg font-semibold text-gray-900 dark:text-white/90">Editar morador</h3>
      {resident && (
        <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
          {resident.name} · {formatPhoneBR(resident.phone_number)}
        </p>
      )}
      <form className="mt-5 space-y-4" onSubmit={(e) => void handleSubmit(onSubmit)(e)}>
        <div>
          <Label>Condomínio / Mercado</Label>
          <select
            className="h-11 w-full rounded-lg border border-gray-300 bg-transparent px-4 py-2.5 text-sm shadow-theme-xs dark:border-gray-700 dark:bg-gray-900 dark:text-white/90"
            {...register("market_id")}
          >
            {markets.map((m) => (
              <option key={m.id} value={m.id}>
                {m.name}
              </option>
            ))}
          </select>
          {errors.market_id && (
            <p className="mt-1 text-xs text-error-500">{errors.market_id.message}</p>
          )}
        </div>
        <div className="flex flex-wrap justify-end gap-3 pt-2">
          <Button type="button" variant="outline" onClick={onClose} disabled={busy}>
            Cancelar
          </Button>
          <Button type="submit" disabled={busy}>
            {busy ? "Salvando…" : "Salvar"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}

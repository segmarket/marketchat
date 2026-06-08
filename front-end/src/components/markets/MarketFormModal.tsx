import { useEffect, useState } from "react";
import { Controller, useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { IMaskInput } from "react-imask";
import { toast } from "sonner";
import { BR_UF_SIGLAS } from "../../constants/brazilUF";
import Label from "../form/Label";
import Input from "../form/input/InputField";
import Switch from "../form/switch/Switch";
import { Modal } from "../ui/modal";
import Button from "../ui/button/Button";
import { createMarket, updateMarket } from "../../features/markets/api";
import {
  formatMarketAddressForApi,
  parseMarketAddress,
  type MarketAddressParts,
} from "../../features/markets/addressFormat";
import {
  marketFormSchema,
  type MarketFormValues,
} from "../../features/markets/schemas";
import type { Market } from "../../features/markets/types";
import { digitsOnly } from "../../utils/cpfCnpj";
import { getAxiosErrorMessage } from "../../utils/apiError";

type Props = {
  isOpen: boolean;
  mode: "create" | "edit";
  market: Market | null;
  onClose: () => void;
  onSaved: () => void;
};

function addressToFormValues(parts: MarketAddressParts, status: MarketFormValues["status"]): MarketFormValues {
  return {
    name: "",
    cep: parts.cep,
    street: parts.street,
    number: parts.number,
    complement: parts.complement,
    neighborhood: parts.neighborhood,
    city: parts.city,
    state: parts.state,
    status,
  };
}

function toDefaultValues(market: Market | null): MarketFormValues {
  if (!market) {
    return addressToFormValues(parseMarketAddress(""), "active");
  }
  const parts = parseMarketAddress(market.address);
  return {
    ...addressToFormValues(parts, market.status),
    name: market.name,
  };
}

export default function MarketFormModal({ isOpen, mode, market, onClose, onSaved }: Props) {
  const [cepLoading, setCepLoading] = useState(false);
  const [cepLookupFailed, setCepLookupFailed] = useState(false);

  const {
    register,
    control,
    handleSubmit,
    reset,
    getValues,
    setValue,
    setFocus,
    formState: { errors, isSubmitting },
  } = useForm<MarketFormValues>({
    resolver: zodResolver(marketFormSchema),
    defaultValues: toDefaultValues(market),
  });

  useEffect(() => {
    if (isOpen) {
      reset(toDefaultValues(market));
      setCepLookupFailed(false);
    }
  }, [isOpen, market, reset]);

  async function handleCepBlur() {
    const cep = digitsOnly(getValues("cep"));
    if (cep.length !== 8) {
      setCepLookupFailed(false);
      return;
    }
    setCepLoading(true);
    try {
      const res = await fetch(`https://viacep.com.br/ws/${cep}/json/`);
      const data = (await res.json()) as {
        erro?: boolean;
        logradouro?: string;
        bairro?: string;
        localidade?: string;
        uf?: string;
      };
      if (data.erro) {
        setCepLookupFailed(true);
        toast.error("CEP não encontrado. Preencha o endereço manualmente.");
        return;
      }
      setCepLookupFailed(false);
      if (data.logradouro) setValue("street", data.logradouro);
      if (data.bairro) setValue("neighborhood", data.bairro);
      if (data.localidade) setValue("city", data.localidade);
      if (data.uf) setValue("state", data.uf);
      toast.success("Endereço preenchido pelo CEP.");
      setTimeout(() => setFocus("number"), 0);
    } catch {
      setCepLookupFailed(true);
      toast.error("Falha ao consultar CEP. Preencha o endereço manualmente.");
    } finally {
      setCepLoading(false);
    }
  }

  async function onSubmit(values: MarketFormValues) {
    const payload = {
      name: values.name,
      address: formatMarketAddressForApi({
        cep: values.cep,
        street: values.street,
        number: values.number,
        complement: values.complement ?? "",
        neighborhood: values.neighborhood,
        city: values.city,
        state: values.state,
      }),
      status: values.status,
    };

    try {
      if (mode === "create") {
        await createMarket(payload);
        toast.success("Mercado cadastrado com sucesso.");
      } else if (market) {
        await updateMarket(market.id, payload);
        toast.success("Mercado atualizado com sucesso.");
      }
      onSaved();
      onClose();
    } catch (err) {
      toast.error(
        getAxiosErrorMessage(err, {
          notAxiosMessage:
            mode === "create" ? "Falha ao cadastrar mercado." : "Falha ao atualizar mercado.",
        }),
      );
    }
  }

  const title = mode === "create" ? "Adicionar novo mercado" : "Editar mercado";

  return (
    <Modal isOpen={isOpen} onClose={onClose} className="max-w-xl p-6">
      <h3 className="text-lg font-semibold text-gray-900 dark:text-white/90">{title}</h3>
      <form className="mt-5 space-y-4" onSubmit={(e) => void handleSubmit(onSubmit)(e)}>
        <div>
          <Label>Nome do Condomínio</Label>
          <Input
            placeholder="Ex.: Condomínio Vista Alegre - Bloco B"
            error={Boolean(errors.name)}
            hint={errors.name?.message}
            {...register("name")}
          />
        </div>

        <div className="space-y-4 rounded-xl border border-gray-100 p-4 dark:border-white/[0.06]">
          <p className="text-sm font-medium text-gray-800 dark:text-white/90">Endereço</p>

          <div>
            <Label>CEP</Label>
            <Controller
              name="cep"
              control={control}
              render={({ field }) => (
                <IMaskInput
                  mask="00000-000"
                  value={field.value}
                  unmask={false}
                  onAccept={(value: string) => {
                    field.onChange(value);
                    setCepLookupFailed(false);
                  }}
                  onBlur={() => {
                    field.onBlur();
                    void handleCepBlur();
                  }}
                  inputRef={field.ref}
                  className={`h-11 w-full rounded-lg border bg-transparent px-4 py-2.5 text-sm shadow-theme-xs dark:text-white/90 ${
                    errors.cep
                      ? "border-error-500 focus:border-error-500 focus:ring-error-500/20"
                      : "border-gray-300 focus:border-brand-300 focus:ring-3 focus:ring-brand-500/10 dark:border-gray-700 dark:bg-gray-900"
                  }`}
                  placeholder="00000-000"
                />
              )}
            />
            {cepLoading && (
              <p className="mt-1 text-xs text-gray-500 animate-pulse dark:text-gray-400">Consultando CEP…</p>
            )}
            {cepLookupFailed && (
              <p className="mt-1 text-xs text-gray-600 dark:text-gray-400">
                CEP não localizado. Preencha rua, bairro, cidade e UF manualmente.
              </p>
            )}
            {errors.cep && <p className="mt-1 text-xs text-error-500">{errors.cep.message}</p>}
          </div>

          <div>
            <Label>Rua</Label>
            <Input
              placeholder="Ex.: Av. Principal"
              error={Boolean(errors.street)}
              hint={errors.street?.message}
              {...register("street")}
            />
          </div>

          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <div>
              <Label>Número</Label>
              <Input
                placeholder="123"
                error={Boolean(errors.number)}
                hint={errors.number?.message}
                {...register("number")}
              />
            </div>
            <div>
              <Label>Complemento</Label>
              <Input placeholder="Bloco B, apto 101" {...register("complement")} />
            </div>
          </div>

          <div>
            <Label>Bairro</Label>
            <Input
              placeholder="Ex.: Centro"
              error={Boolean(errors.neighborhood)}
              hint={errors.neighborhood?.message}
              {...register("neighborhood")}
            />
          </div>

          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <div>
              <Label>Cidade</Label>
              <Input
                placeholder="Ex.: Campinas"
                error={Boolean(errors.city)}
                hint={errors.city?.message}
                {...register("city")}
              />
            </div>
            <div>
              <Label>UF</Label>
              <Controller
                name="state"
                control={control}
                render={({ field }) => (
                  <select
                    {...field}
                    className={`h-11 w-full appearance-none rounded-lg border bg-transparent px-4 py-2.5 text-sm shadow-theme-xs dark:text-white/90 ${
                      errors.state
                        ? "border-error-500"
                        : "border-gray-300 focus:border-brand-300 focus:ring-3 focus:ring-brand-500/10 dark:border-gray-700 dark:bg-gray-900"
                    }`}
                  >
                    <option value="">Selecione</option>
                    {BR_UF_SIGLAS.map((uf) => (
                      <option key={uf} value={uf}>
                        {uf}
                      </option>
                    ))}
                  </select>
                )}
              />
              {errors.state && <p className="mt-1 text-xs text-error-500">{errors.state.message}</p>}
            </div>
          </div>
        </div>

        <div>
          <Controller
            name="status"
            control={control}
            render={({ field }) => (
              <Switch
                key={`${mode}-${market?.id ?? "new"}-${field.value}`}
                label="Mercado ativo"
                defaultChecked={field.value === "active"}
                onChange={(checked) => field.onChange(checked ? "active" : "inactive")}
              />
            )}
          />
        </div>

        <div className="mt-6 flex flex-wrap justify-end gap-3">
          <Button type="button" variant="outline" onClick={onClose} disabled={isSubmitting}>
            Cancelar
          </Button>
          <Button type="submit" disabled={isSubmitting}>
            {isSubmitting ? "Salvando…" : "Salvar"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}

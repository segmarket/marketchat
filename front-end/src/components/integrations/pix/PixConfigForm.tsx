import { useEffect } from "react";
import { Controller, useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { IMaskInput } from "react-imask";
import { Link } from "react-router";
import Label from "../../form/Label";
import Input from "../../form/input/InputField";
import Button from "../../ui/button/Button";
import {
  PIX_KEY_TYPE_OPTIONS,
  pixConfigFormSchema,
  type PixConfigFormValues,
} from "../../../features/integrations/pix/schemas";
import { pixKeyMaskForType, pixKeyPlaceholder } from "../../../features/integrations/pix/pixKeyMask";
import type { PixConfig } from "../../../features/integrations/pix/types";

type Props = {
  config: PixConfig;
  disabled: boolean;
  submitting: boolean;
  onSubmit: (values: PixConfigFormValues) => void;
};

function configToFormValues(config: PixConfig): PixConfigFormValues {
  return {
    name: config.name || config.prefill.name,
    email: config.email || config.prefill.email,
    cpf_cnpj: config.cpf_cnpj || config.prefill.cpf_cnpj,
    pix_key_type: config.pix_key_type || "CPF",
    pix_key: config.pix_key || "",
  };
}

export default function PixConfigForm({ config, disabled, submitting, onSubmit }: Props) {
  const {
    register,
    control,
    handleSubmit,
    reset,
    watch,
    formState: { errors },
  } = useForm<PixConfigFormValues>({
    resolver: zodResolver(pixConfigFormSchema),
    defaultValues: configToFormValues(config),
  });

  const pixKeyType = watch("pix_key_type");
  const pixMask = pixKeyMaskForType(pixKeyType);

  useEffect(() => {
    reset(configToFormValues(config));
  }, [config, reset]);

  return (
    <form className="space-y-4" onSubmit={(e) => void handleSubmit(onSubmit)(e)}>
      {!config.has_market_address && (
        <div className="rounded-lg border border-warning-200 bg-warning-50 p-3 text-sm text-warning-800 dark:border-warning-500/30 dark:bg-warning-500/10 dark:text-warning-100">
          Cadastre ao menos um mercado com endereço completo em{" "}
          <Link to="/admin/markets" className="font-medium underline">
            Meus Mercados
          </Link>{" "}
          antes de salvar as configurações Pix.
        </div>
      )}

      <div>
        <Label>Nome completo ou razão social do titular</Label>
        <Input
          placeholder="Nome do recebedor"
          disabled={disabled}
          error={Boolean(errors.name)}
          hint={errors.name?.message}
          {...register("name")}
        />
      </div>

      <div>
        <Label>CPF ou CNPJ</Label>
        <Controller
          name="cpf_cnpj"
          control={control}
          render={({ field }) => (
            <IMaskInput
              mask={[{ mask: "000.000.000-00" }, { mask: "00.000.000/0000-00" }]}
              dispatch={(appended, dynamicMasked) => {
                const combined = `${dynamicMasked.value}${appended}`;
                const n = combined.replace(/\D/g, "").slice(0, 14);
                const idx = n.length > 11 ? 1 : 0;
                return dynamicMasked.compiledMasks[idx]!;
              }}
              value={field.value}
              unmask={false}
              disabled={disabled}
              onAccept={(value: string) => field.onChange(value)}
              onBlur={field.onBlur}
              inputRef={field.ref}
              className={`h-11 w-full rounded-lg border bg-transparent px-4 py-2.5 text-sm shadow-theme-xs dark:text-white/90 ${
                errors.cpf_cnpj
                  ? "border-error-500"
                  : "border-gray-300 dark:border-gray-700"
              }`}
              placeholder="00.000.000/0000-00"
            />
          )}
        />
        {errors.cpf_cnpj && <p className="mt-1 text-xs text-error-500">{errors.cpf_cnpj.message}</p>}
      </div>

      <div>
        <Label>E-mail comercial</Label>
        <Input
          type="email"
          placeholder="contato@empresa.com"
          disabled={disabled}
          error={Boolean(errors.email)}
          hint={errors.email?.message}
          {...register("email")}
        />
      </div>

      <div>
        <Label>Tipo de chave Pix</Label>
        <select
          disabled={disabled}
          className="h-11 w-full rounded-lg border border-gray-300 bg-transparent px-4 py-2.5 text-sm shadow-theme-xs dark:border-gray-700 dark:bg-gray-900 dark:text-white/90"
          {...register("pix_key_type")}
        >
          {PIX_KEY_TYPE_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
      </div>

      <div>
        <Label>Chave Pix</Label>
        {pixMask.mask ? (
          <Controller
            name="pix_key"
            control={control}
            render={({ field }) => (
              <IMaskInput
                mask={pixMask.mask}
                value={field.value}
                unmask={false}
                disabled={disabled}
                onAccept={(value: string) => field.onChange(value)}
                onBlur={field.onBlur}
                inputRef={field.ref}
                className={`h-11 w-full rounded-lg border bg-transparent px-4 py-2.5 text-sm shadow-theme-xs dark:text-white/90 ${
                  errors.pix_key ? "border-error-500" : "border-gray-300 dark:border-gray-700"
                }`}
                placeholder={pixKeyPlaceholder(pixKeyType)}
              />
            )}
          />
        ) : (
          <Input
            placeholder={pixKeyPlaceholder(pixKeyType)}
            disabled={disabled}
            error={Boolean(errors.pix_key)}
            {...register("pix_key")}
          />
        )}
        {errors.pix_key && <p className="mt-1 text-xs text-error-500">{errors.pix_key.message}</p>}
      </div>

      <div className="pt-2">
        <Button type="submit" disabled={disabled || submitting || !config.has_market_address}>
          {submitting ? (
            <span className="inline-flex items-center gap-2">
              <span className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
              Salvando…
            </span>
          ) : (
            "Salvar Configurações Pix"
          )}
        </Button>
      </div>
    </form>
  );
}

import { useEffect, useState, type FocusEvent } from "react";
import { useForm, Controller } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { IMaskInput } from "react-imask";
import Cards from "react-credit-cards-2";
import "react-credit-cards-2/dist/es/styles-compiled.css";
import { toast } from "sonner";
import axios from "axios";
import Label from "../form/Label";
import Input from "../form/input/InputField";
import Button from "../ui/button/Button";
import { UF_SELECT_OPTIONS } from "../../constants/brazilUF";
import { updateCardSchema, type UpdateCardFormValues } from "../../features/settings/schemas";
import { updatePaymentMethod, type UpdateCardPayload } from "../../features/settings/api";
import type { AccountSettingsResponse, PaymentMethodSummary } from "../../features/settings/types";
import { getAxiosErrorMessage } from "../../utils/apiError";
import { digitsOnly } from "../../utils/cpfCnpj";

export function defaultHolder(account: AccountSettingsResponse): Partial<UpdateCardFormValues> {
  const u = account.user;
  const t = account.tenant;
  return {
    name: [u.first_name, u.last_name].filter(Boolean).join(" ") || u.email,
    email: u.email,
    cpfCnpj: t?.cpf_cnpj ?? "",
    phone: t?.phone || u.phone || "",
    postalCode: "",
    address: "",
    addressNumber: "",
    complement: "",
    province: "",
    cardNumber: "",
    cardName: "",
    cardExpiry: "",
    cardCvv: "",
  };
}

type UpdateCardFormProps = {
  accountData: AccountSettingsResponse;
  onSuccess: (summary: PaymentMethodSummary) => void;
  submitLabel?: string;
  showCancel?: boolean;
  onCancel?: () => void;
};

export default function UpdateCardForm({
  accountData,
  onSuccess,
  submitLabel = "Salvar cartão",
  showCancel = false,
  onCancel,
}: UpdateCardFormProps) {
  const [cardFocus, setCardFocus] = useState<"" | "name" | "number" | "expiry" | "cvc">("");
  const [submitting, setSubmitting] = useState(false);
  const cpfLocked = !(accountData.tenant?.cpf_cnpj_editable ?? true);

  const {
    register,
    control,
    handleSubmit,
    reset,
    watch,
    formState: { errors },
  } = useForm<UpdateCardFormValues>({
    resolver: zodResolver(updateCardSchema),
    defaultValues: defaultHolder(accountData) as UpdateCardFormValues,
  });

  useEffect(() => {
    reset(defaultHolder(accountData) as UpdateCardFormValues);
  }, [accountData, reset]);

  const cardNumber = watch("cardNumber");
  const cardName = watch("cardName");
  const cardExpiry = watch("cardExpiry");
  const cardCvv = watch("cardCvv");
  const cardFocused = cardFocus === "" ? undefined : (cardFocus as "name" | "number" | "expiry" | "cvc");

  async function onSubmit(data: UpdateCardFormValues) {
    const [mm, yy] = data.cardExpiry.split("/");
    const y4 = parseInt(yy!, 10) >= 70 ? `19${yy}` : `20${yy}`;
    const holder: UpdateCardPayload["credit_card_holder"] = {
      name: data.name.trim(),
      email: data.email,
      postalCode: digitsOnly(data.postalCode),
      address: data.address,
      addressNumber: data.addressNumber,
      complement: data.complement || "",
      province: data.province,
      phone: digitsOnly(data.phone),
    };
    const cpf = digitsOnly(data.cpfCnpj || "");
    if (cpf) holder.cpfCnpj = cpf;

    const payload: UpdateCardPayload = {
      credit_card: {
        holderName: data.cardName,
        number: digitsOnly(data.cardNumber),
        expiryMonth: mm!.padStart(2, "0"),
        expiryYear: y4,
        ccv: data.cardCvv,
      },
      credit_card_holder: holder,
    };

    setSubmitting(true);
    try {
      const summary = await updatePaymentMethod(payload);
      toast.success("Cartão atualizado com sucesso.");
      onSuccess(summary);
    } catch (e: unknown) {
      if (axios.isAxiosError(e) && e.response?.status === 502) {
        toast.error("Serviço de pagamentos temporariamente indisponível.");
      } else {
        toast.error(getAxiosErrorMessage(e));
      }
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
      <div className="flex justify-center">
        <Cards
          number={digitsOnly(cardNumber)}
          name={cardName}
          expiry={cardExpiry}
          cvc={cardCvv}
          focused={cardFocused}
          locale={{ valid: "Válido até" }}
        />
      </div>
      <div className="grid gap-4 sm:grid-cols-2">
        <div className="sm:col-span-2">
          <Label>Número do cartão</Label>
          <Controller
            name="cardNumber"
            control={control}
            render={({ field }) => (
              <IMaskInput
                mask="0000 0000 0000 0000"
                value={field.value}
                unmask={false}
                onAccept={(v: string) => field.onChange(v)}
                onFocus={() => setCardFocus("number")}
                onBlur={() => {
                  setCardFocus("");
                  field.onBlur();
                }}
                inputRef={field.ref}
                className="h-11 w-full rounded-lg border border-gray-300 px-4 text-sm dark:border-gray-700 dark:text-white/90"
              />
            )}
          />
          {errors.cardNumber && (
            <p className="mt-1 text-xs text-error-500">{errors.cardNumber.message}</p>
          )}
        </div>
        <div className="sm:col-span-2">
          <Label>Nome no cartão</Label>
          <Input
            {...(() => {
              const r = register("cardName");
              return {
                ...r,
                onFocus: () => setCardFocus("name"),
                onBlur: (e: FocusEvent<HTMLInputElement>) => {
                  setCardFocus("");
                  void r.onBlur(e);
                },
              };
            })()}
            error={!!errors.cardName}
          />
          {errors.cardName && (
            <p className="mt-1 text-xs text-error-500">{errors.cardName.message}</p>
          )}
        </div>
        <div>
          <Label>Validade</Label>
          <Controller
            name="cardExpiry"
            control={control}
            render={({ field }) => (
              <IMaskInput
                mask="00/00"
                value={field.value}
                unmask={false}
                onAccept={(v: string) => field.onChange(v)}
                onFocus={() => setCardFocus("expiry")}
                onBlur={() => {
                  setCardFocus("");
                  field.onBlur();
                }}
                inputRef={field.ref}
                className="h-11 w-full rounded-lg border border-gray-300 px-4 text-sm dark:border-gray-700"
                placeholder="MM/AA"
              />
            )}
          />
        </div>
        <div>
          <Label>CVV</Label>
          <Controller
            name="cardCvv"
            control={control}
            render={({ field }) => (
              <IMaskInput
                mask="0000"
                value={field.value}
                unmask={false}
                onAccept={(v: string) => field.onChange(v)}
                onFocus={() => setCardFocus("cvc")}
                onBlur={() => {
                  setCardFocus("");
                  field.onBlur();
                }}
                inputRef={field.ref}
                className="h-11 w-full rounded-lg border border-gray-300 px-4 text-sm dark:border-gray-700"
                type="password"
              />
            )}
          />
        </div>
      </div>
      <div className="border-t border-gray-100 pt-4 dark:border-gray-800">
        <p className="mb-3 text-sm font-medium text-gray-700 dark:text-gray-300">Titular do cartão</p>
        <div className="grid gap-4 sm:grid-cols-2">
          <div className="sm:col-span-2">
            <Label>Nome</Label>
            <Input {...register("name")} />
          </div>
          <div>
            <Label>E-mail</Label>
            <Input type="email" {...register("email")} />
          </div>
          <div>
            <Label>Telefone</Label>
            <Input {...register("phone")} />
          </div>
          <div>
            <Label>CPF/CNPJ</Label>
            <Input disabled={cpfLocked} {...register("cpfCnpj")} />
          </div>
          <div>
            <Label>CEP</Label>
            <Input {...register("postalCode")} />
          </div>
          <div className="sm:col-span-2">
            <Label>Endereço</Label>
            <Input {...register("address")} />
          </div>
          <div>
            <Label>Número</Label>
            <Input {...register("addressNumber")} />
          </div>
          <div>
            <Label>UF</Label>
            <select
              {...register("province")}
              className="h-11 w-full rounded-lg border border-gray-300 px-4 text-sm dark:border-gray-700 dark:bg-gray-900"
            >
              <option value="">UF</option>
              {UF_SELECT_OPTIONS.map((o) => (
                <option key={o.value} value={o.value}>
                  {o.label}
                </option>
              ))}
            </select>
          </div>
        </div>
      </div>
      <div className="flex justify-end gap-3">
        {showCancel && onCancel && (
          <Button type="button" variant="outline" onClick={onCancel}>
            Cancelar
          </Button>
        )}
        <Button type="submit" disabled={submitting}>
          {submitting ? "Salvando…" : submitLabel}
        </Button>
      </div>
    </form>
  );
}

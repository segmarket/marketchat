import { useEffect, useState } from "react";
import { useForm, Controller } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { IMaskInput } from "react-imask";
import { toast } from "sonner";
import Label from "../form/Label";
import Input from "../form/input/InputField";
import Button from "../ui/button/Button";
import FormSection from "../layout/FormSection";
import FormSectionActions from "../layout/FormSectionActions";
import {
  FIELD_HINT_CLASS,
  LOCKED_INPUT_CLASS,
  LOCKED_MASK_INPUT_CLASS,
} from "../form/lockedInputClasses";
import { patchAccountSettings } from "../../features/settings/api";
import {
  accountSettingsSchema,
  validateAccountSettings,
  type AccountSettingsFormValues,
} from "../../features/settings/schemas";
import type { AccountSettingsResponse } from "../../features/settings/types";
import { getAxiosErrorMessage } from "../../utils/apiError";
import { digitsOnly } from "../../utils/cpfCnpj";

const MASK_INPUT_CLASS =
  "h-11 w-full rounded-lg border border-gray-300 bg-transparent px-4 py-2.5 text-sm shadow-theme-xs placeholder:text-gray-400 focus:border-brand-300 focus:outline-none focus:ring-2 focus:ring-brand-500/20 dark:border-gray-700 dark:text-white/90";

type AccountSettingsFormProps = {
  data: AccountSettingsResponse;
  onUpdated: (data: AccountSettingsResponse) => void;
};

function toFormValues(data: AccountSettingsResponse): AccountSettingsFormValues {
  return {
    first_name: data.user.first_name,
    last_name: data.user.last_name,
    phone: data.user.phone,
    tenant_name: data.tenant?.name ?? "",
    tenant_phone: data.tenant?.phone ?? "",
    cpf_cnpj: data.tenant?.cpf_cnpj ?? "",
  };
}

export default function AccountSettingsForm({ data, onUpdated }: AccountSettingsFormProps) {
  const [submitting, setSubmitting] = useState(false);
  const isAdmin = data.user.can_manage_integrations ?? data.user.is_tenant_admin;
  const cpfEditable = data.tenant?.cpf_cnpj_editable ?? false;

  const { register, control, handleSubmit, reset } = useForm<AccountSettingsFormValues>({
    resolver: zodResolver(accountSettingsSchema),
    defaultValues: toFormValues(data),
  });

  useEffect(() => {
    reset(toFormValues(data));
  }, [data, reset]);

  async function onSubmit(values: AccountSettingsFormValues) {
    const validationError = validateAccountSettings(values, {
      isTenantAdmin: isAdmin,
      cpfCnpjEditable: cpfEditable,
    });
    if (validationError) {
      toast.error(validationError);
      return;
    }

    const payload: Record<string, string> = {
      first_name: values.first_name,
      last_name: values.last_name,
      phone: digitsOnly(values.phone),
    };
    if (isAdmin && data.tenant) {
      if (values.tenant_name) payload.tenant_name = values.tenant_name;
      payload.tenant_phone = digitsOnly(values.tenant_phone ?? "");
      if (cpfEditable && values.cpf_cnpj) {
        payload.cpf_cnpj = digitsOnly(values.cpf_cnpj);
      }
    }

    setSubmitting(true);
    try {
      const updated = await patchAccountSettings(payload);
      onUpdated(updated);
      toast.success("Alterações salvas.");
    } catch (e: unknown) {
      toast.error(getAxiosErrorMessage(e));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-8">
      <FormSection
        title="Dados pessoais"
        description="Atualize suas informações de contato e credenciais de acesso."
      >
        <div className="grid gap-5 sm:grid-cols-2">
          <div>
            <Label>Nome</Label>
            <Input placeholder="Nome" {...register("first_name")} />
          </div>
          <div>
            <Label>Sobrenome</Label>
            <Input placeholder="Sobrenome" {...register("last_name")} />
          </div>
          <div>
            <Label>Telefone</Label>
            <Controller
              name="phone"
              control={control}
              render={({ field }) => (
                <IMaskInput
                  mask="(00) 00000-0000"
                  value={field.value}
                  unmask={false}
                  onAccept={(v: string) => field.onChange(v)}
                  onBlur={field.onBlur}
                  inputRef={field.ref}
                  className={MASK_INPUT_CLASS}
                  placeholder="(11) 99999-9999"
                />
              )}
            />
          </div>
          <div>
            <Label>E-mail</Label>
            <Input type="email" value={data.user.email} disabled className={LOCKED_INPUT_CLASS} />
            <p className={FIELD_HINT_CLASS}>O e-mail não pode ser alterado aqui.</p>
          </div>
        </div>
      </FormSection>

      {data.tenant && (
        <FormSection
          title="Empresa"
          description="Dados da empresa vinculada à sua conta. Administradores podem editar nome e telefone."
        >
          <div className="grid gap-5 sm:grid-cols-2">
            <div className="sm:col-span-2">
              <Label>Nome da empresa</Label>
              <Input
                placeholder="Razão social ou nome fantasia"
                disabled={!isAdmin}
                className={!isAdmin ? LOCKED_INPUT_CLASS : undefined}
                {...register("tenant_name")}
              />
            </div>
            <div>
              <Label>Telefone da empresa</Label>
              <Controller
                name="tenant_phone"
                control={control}
                render={({ field }) => (
                  <IMaskInput
                    mask="(00) 00000-0000"
                    value={field.value}
                    disabled={!isAdmin}
                    unmask={false}
                    onAccept={(v: string) => field.onChange(v)}
                    onBlur={field.onBlur}
                    inputRef={field.ref}
                    className={!isAdmin ? LOCKED_MASK_INPUT_CLASS : MASK_INPUT_CLASS}
                  />
                )}
              />
            </div>
            <div>
              <Label>CPF / CNPJ</Label>
              <Input
                placeholder="000.000.000-00"
                disabled={!isAdmin || !cpfEditable}
                className={!isAdmin || !cpfEditable ? LOCKED_INPUT_CLASS : undefined}
                {...register("cpf_cnpj")}
              />
              {!cpfEditable && (
                <p className={FIELD_HINT_CLASS}>Não pode ser alterado após o cadastro.</p>
              )}
            </div>
          </div>
          {!isAdmin && (
            <p className="mt-5 border-t border-gray-100 pt-4 text-sm text-gray-500 dark:border-gray-800 dark:text-gray-400">
              Apenas administradores da empresa podem alterar os dados da empresa.
            </p>
          )}
        </FormSection>
      )}

      <FormSectionActions>
        <Button type="submit" disabled={submitting}>
          {submitting ? "Salvando…" : "Salvar alterações"}
        </Button>
      </FormSectionActions>
    </form>
  );
}

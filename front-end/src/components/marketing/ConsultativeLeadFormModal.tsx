import { useEffect, useState } from "react";
import { Controller, useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { IMaskInput } from "react-imask";
import { MessageCircle } from "lucide-react";
import { toast } from "sonner";
import Label from "../form/Label";
import Input from "../form/input/InputField";
import Button from "../ui/button/Button";
import { Modal } from "../ui/modal";
import { ANALYTICS_EVENTS } from "../../constants/analyticsEvents";
import {
  CONSULTATIVE_FORM_CTA,
  CONSULTATIVE_FORM_DESCRIPTION,
  CONSULTATIVE_FORM_TITLE,
  CONSULTATIVE_SUCCESS_BODY,
  CONSULTATIVE_SUCCESS_TITLE,
  CONSULTATIVE_WHATSAPP_CTA,
  CTA_PRIMARY_CLASS,
} from "../../constants/marketingCopy";
import { WHATSAPP_SUPPORT_URL } from "../../constants/marketingUrls";
import {
  consultativeLeadSchema,
  type ConsultativeLeadValues,
} from "../../features/consultative/schema";
import { api } from "../../services/api";
import { trackEvent } from "../../utils/analytics";
import { getAxiosErrorMessage } from "../../utils/apiError";
import { digitsOnly } from "../../utils/cpfCnpj";

type Step = "form" | "success";

type ConsultativeLeadFormModalProps = {
  isOpen: boolean;
  onClose: () => void;
};

export default function ConsultativeLeadFormModal({
  isOpen,
  onClose,
}: ConsultativeLeadFormModalProps) {
  const [step, setStep] = useState<Step>("form");
  const [submitting, setSubmitting] = useState(false);

  const {
    register,
    control,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<ConsultativeLeadValues>({
    resolver: zodResolver(consultativeLeadSchema),
    defaultValues: { fullName: "", phone: "", email: "" },
    mode: "onBlur",
  });

  useEffect(() => {
    if (!isOpen) {
      setStep("form");
      reset();
      setSubmitting(false);
    }
  }, [isOpen, reset]);

  async function onSubmit(data: ConsultativeLeadValues) {
    setSubmitting(true);
    try {
      await api.post("/api/auth/consultative-lead/", {
        full_name: data.fullName.trim(),
        email: data.email.trim(),
        phone: digitsOnly(data.phone),
      });
      trackEvent(ANALYTICS_EVENTS.LEAD_GENERATED);
      setStep("success");
    } catch (e: unknown) {
      toast.error(getAxiosErrorMessage(e));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Modal isOpen={isOpen} onClose={onClose} className="max-w-md p-6 sm:p-8">
      {step === "form" ? (
        <>
          <h2 className="pr-8 text-xl font-bold text-gray-900">{CONSULTATIVE_FORM_TITLE}</h2>
          <p className="mt-2 text-sm leading-relaxed text-gray-600">
            {CONSULTATIVE_FORM_DESCRIPTION}
          </p>
          <form className="mt-6 space-y-4" onSubmit={handleSubmit(onSubmit)} noValidate>
            <div>
              <Label>
                Nome completo <span className="text-error-500">*</span>
              </Label>
              <Input
                {...register("fullName")}
                placeholder="Seu nome"
                error={!!errors.fullName}
              />
              {errors.fullName && (
                <p className="mt-1 text-xs text-error-500">{errors.fullName.message}</p>
              )}
            </div>
            <div>
              <Label>
                Telefone (WhatsApp) <span className="text-error-500">*</span>
              </Label>
              <Controller
                name="phone"
                control={control}
                render={({ field }) => (
                  <IMaskInput
                    mask="(00) 00000-0000"
                    value={field.value}
                    unmask={false}
                    onAccept={(value: string) => field.onChange(value)}
                    onBlur={field.onBlur}
                    inputRef={field.ref}
                    className={`h-11 w-full rounded-lg border bg-transparent px-4 py-2.5 text-sm shadow-theme-xs dark:text-white/90 ${
                      errors.phone
                        ? "border-error-500 focus:border-error-500 focus:ring-error-500/20"
                        : "border-gray-300 dark:border-gray-700"
                    }`}
                    placeholder="(11) 99999-9999"
                  />
                )}
              />
              {errors.phone && (
                <p className="mt-1 text-xs text-error-500">{errors.phone.message}</p>
              )}
            </div>
            <div>
              <Label>
                E-mail <span className="text-error-500">*</span>
              </Label>
              <Input
                {...register("email")}
                type="email"
                placeholder="seu@email.com"
                error={!!errors.email}
              />
              {errors.email && (
                <p className="mt-1 text-xs text-error-500">{errors.email.message}</p>
              )}
            </div>
            <Button
              type="submit"
              className={`w-full ${CTA_PRIMARY_CLASS}`}
              disabled={submitting}
            >
              {submitting ? "Enviando…" : CONSULTATIVE_FORM_CTA}
            </Button>
          </form>
        </>
      ) : (
        <div className="text-center">
          <h2 className="pr-8 text-xl font-bold text-gray-900">{CONSULTATIVE_SUCCESS_TITLE}</h2>
          <p className="mt-3 text-gray-600">{CONSULTATIVE_SUCCESS_BODY}</p>
          <a
            href={WHATSAPP_SUPPORT_URL}
            target="_blank"
            rel="noopener noreferrer"
            className={`mt-6 inline-flex min-h-[48px] w-full items-center justify-center gap-2 ${CTA_PRIMARY_CLASS} px-6`}
          >
            <MessageCircle className="size-5" aria-hidden />
            {CONSULTATIVE_WHATSAPP_CTA}
          </a>
        </div>
      )}
    </Modal>
  );
}

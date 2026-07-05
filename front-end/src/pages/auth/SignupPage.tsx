import { useEffect, useState } from "react";
import type { FocusEvent } from "react";
import { Link, useNavigate } from "react-router";
import { useForm, Controller, type Resolver } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { IMaskInput } from "react-imask";
import Cards from "react-credit-cards-2";
import "react-credit-cards-2/dist/es/styles-compiled.css";
import { toast } from "sonner";
import { ChevronLeftIcon, EyeCloseIcon, EyeIcon } from "../../icons";
import Label from "../../components/form/Label";
import Input from "../../components/form/input/InputField";
import Button from "../../components/ui/button/Button";
import PageMeta from "../../components/common/PageMeta";
import AuthLayout from "../AuthPages/AuthPageLayout";
import SignupProgressBar from "../../components/auth/signup/SignupProgressBar";
import PasswordStrengthMeter from "../../components/auth/signup/PasswordStrengthMeter";
import TrialSummaryCard from "../../components/auth/signup/TrialSummaryCard";
import Checkbox from "../../components/form/input/Checkbox";
import { UF_SELECT_OPTIONS } from "../../constants/brazilUF";
import {
  fullSignupSchema,
  step1Schema,
  step2Schema,
  type FullSignupValues,
} from "../../features/signup/schema";
import {
  hasAttributionParams,
  loadAttribution,
  parseAttributionFromSearch,
  saveAttribution,
} from "../../features/attribution/storage";
import {
  CONSENT_CHANGE_EVENT,
  hasMarketingConsent,
  type CookieConsentPreferences,
} from "../../features/marketing/cookieConsent";
import { ANALYTICS_EVENTS } from "../../constants/analyticsEvents";
import { api } from "../../services/api";
import {
  buildSignupFunnelPayload,
  getTrialPlanValue,
  hashEmail,
  hashPhone,
  trackEvent,
} from "../../utils/analytics";
import { getAxiosErrorMessage } from "../../utils/apiError";
import { digitsOnly } from "../../utils/cpfCnpj";

const TRIAL_DAYS = 7;

const STEP3_CARD_FIELD_KEYS: (keyof FullSignupValues)[] = ["cardNumber", "cardName", "cardExpiry", "cardCvv"];

function slugify(name: string): string {
  return name
    .normalize("NFD")
    .replace(/\p{M}/gu, "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "")
    .slice(0, 80);
}

export default function SignupPage() {
  const navigate = useNavigate();
  const [step, setStep] = useState<1 | 2 | 3>(1);
  const [showPassword, setShowPassword] = useState(false);
  const [cardFocus, setCardFocus] = useState<"" | "name" | "number" | "expiry" | "cvc">("");
  const [submitting, setSubmitting] = useState(false);
  const [cepLoading, setCepLoading] = useState(false);
  const [cepLookupFailed, setCepLookupFailed] = useState(false);

  useEffect(() => {
    trackEvent(ANALYTICS_EVENTS.BEGIN_SIGNUP);
  }, []);

  useEffect(() => {
    const fromUrl = parseAttributionFromSearch(window.location.search);
    if (hasMarketingConsent()) {
      saveAttribution(fromUrl);
    }

    function onConsentChange(event: Event) {
      const prefs = (event as CustomEvent<CookieConsentPreferences>).detail;
      if (prefs?.marketing) {
        saveAttribution(fromUrl);
      }
    }

    window.addEventListener(CONSENT_CHANGE_EVENT, onConsentChange);
    return () => window.removeEventListener(CONSENT_CHANGE_EVENT, onConsentChange);
  }, []);

  const form = useForm<FullSignupValues>({
    resolver: zodResolver(fullSignupSchema) as Resolver<FullSignupValues>,
    shouldFocusError: false,
    defaultValues: {
      fullName: "",
      email: "",
      password: "",
      company_name: "",
      cpfCnpj: "",
      phone: "",
      cep: "",
      address: "",
      addressNumber: "",
      complement: "",
      province: "",
      cardNumber: "",
      cardName: "",
      cardExpiry: "",
      cardCvv: "",
      acceptTerms: false,
    },
    mode: "onBlur",
    reValidateMode: "onBlur",
  });

  const {
    register,
    control,
    handleSubmit,
    watch,
    trigger,
    setValue,
    getValues,
    setFocus,
    clearErrors,
    formState: { errors },
  } = form;

  useEffect(() => {
    if (step !== 3) return;
    void (async () => {
      const email = getValues("email");
      const phone = getValues("phone");
      const [email_address, phone_number] = await Promise.all([
        hashEmail(email),
        hashPhone(phone),
      ]);
      trackEvent(
        ANALYTICS_EVENTS.INITIATE_CHECKOUT,
        buildSignupFunnelPayload(email_address, phone_number),
      );
    })();
  }, [step, getValues]);

  useEffect(() => {
    if (step !== 3) return;
    const id = window.setTimeout(() => {
      clearErrors(STEP3_CARD_FIELD_KEYS);
      setCardFocus("number");
      setFocus("cardNumber");
    }, 0);
    return () => window.clearTimeout(id);
  }, [step, clearErrors, setFocus]);

  const watchedValues = watch();
  const password = watchedValues.password;
  const canContinueStep =
    step === 1
      ? step1Schema.safeParse({
          fullName: watchedValues.fullName,
          email: watchedValues.email,
          password: watchedValues.password,
          acceptTerms: watchedValues.acceptTerms,
        }).success
      : step2Schema.safeParse({
          company_name: watchedValues.company_name,
          cpfCnpj: watchedValues.cpfCnpj,
          phone: watchedValues.phone,
          cep: watchedValues.cep,
          address: watchedValues.address,
          addressNumber: watchedValues.addressNumber,
          complement: watchedValues.complement,
          province: watchedValues.province,
        }).success;
  const cardNumber = watch("cardNumber");
  const cardName = watch("cardName");
  const cardExpiry = watch("cardExpiry");
  const cardCvv = watch("cardCvv");

  const step1Fields: (keyof FullSignupValues)[] = ["fullName", "email", "password", "acceptTerms"];
  const step2Fields: (keyof FullSignupValues)[] = [
    "company_name",
    "cpfCnpj",
    "phone",
    "cep",
    "address",
    "addressNumber",
    "complement",
    "province",
  ];

  async function goNext() {
    const fields = step === 1 ? step1Fields : step2Fields;
    const ok = await trigger(fields);
    if (!ok) return;
    if (step === 1) {
      trackEvent(ANALYTICS_EVENTS.LEAD_GENERATED);
    }
    setStep((s) => (s + 1) as 1 | 2 | 3);
  }

  function goBack() {
    if (step > 1) setStep((s) => (s - 1) as 1 | 2 | 3);
  }

  async function handleCepBlur() {
    const cep = digitsOnly(getValues("cep"));
    if (cep.length !== 8) {
      setCepLookupFailed(false);
      return;
    }
    setCepLoading(true);
    try {
      const res = await fetch(`https://viacep.com.br/ws/${cep}/json/`);
      const data = (await res.json()) as { erro?: boolean; logradouro?: string; uf?: string; localidade?: string };
      if (data.erro) {
        setCepLookupFailed(true);
        toast.error("CEP não encontrado. Preencha o endereço manualmente e selecione a UF.");
        return;
      }
      setCepLookupFailed(false);
      setValue("address", [data.logradouro, data.localidade].filter(Boolean).join(", ") || "");
      setValue("province", data.uf || "", { shouldValidate: true });
      toast.success("Endereço preenchido pelo CEP.");
      setTimeout(() => setFocus("addressNumber"), 0);
    } catch {
      setCepLookupFailed(true);
      toast.error("Falha ao consultar CEP. Preencha o endereço manualmente e selecione a UF.");
    } finally {
      setCepLoading(false);
    }
  }

  async function submitRegister(data: FullSignupValues) {
    const [hashedEmail, hashedPhone] = await Promise.all([
      hashEmail(data.email),
      hashPhone(data.phone),
    ]);
    trackEvent(
      ANALYTICS_EVENTS.ADD_PAYMENT_INFO,
      buildSignupFunnelPayload(hashedEmail, hashedPhone),
    );

    setSubmitting(true);
    const parts = data.fullName.trim().split(/\s+/);
    const firstName = parts[0] ?? "";
    const lastName = parts.slice(1).join(" ") || firstName;
    const [mm, yy] = data.cardExpiry.split("/");
    const y4 = parseInt(yy!, 10) >= 70 ? `19${yy}` : `20${yy}`;

    const attribution = loadAttribution();
    const payload = {
      company_name: data.company_name,
      tenant_slug: slugify(data.company_name),
      admin_email: data.email,
      admin_password: data.password,
      first_name: firstName,
      last_name: lastName,
      ...(hasAttributionParams(attribution) ? { attribution } : {}),
      credit_card: {
        holderName: data.cardName,
        number: digitsOnly(data.cardNumber),
        expiryMonth: mm!.padStart(2, "0"),
        expiryYear: y4,
        ccv: data.cardCvv,
      },
      credit_card_holder: {
        name: data.fullName.trim(),
        email: data.email,
        cpfCnpj: digitsOnly(data.cpfCnpj),
        postalCode: digitsOnly(data.cep),
        address: data.address,
        addressNumber: data.addressNumber,
        complement: data.complement || "",
        province: data.province,
        phone: digitsOnly(data.phone),
      },
      accept_terms: true,
    };

    try {
      await api.post("/api/auth/register/", payload);
      trackEvent(ANALYTICS_EVENTS.SIGN_UP, { method: "email" });
      const trialValue = getTrialPlanValue();
      const startTrialPayload: Record<string, unknown> = {
        currency: "BRL",
      };
      if (hashedEmail) startTrialPayload.hashed_email = hashedEmail;
      if (hashedPhone) startTrialPayload.hashed_phone = hashedPhone;
      if (trialValue !== undefined) {
        startTrialPayload.value = trialValue;
      }
      /*
       * GUARDRAIL — start_trial (Meta StartTrial via GTM):
       * Disparar SOMENTE aqui, após POST /api/auth/register/ bem-sucedido.
       * NÃO mover para useEffect de montagem, clique no CTA da landing, goNext()
       * ou Passo 3 — eventos precoces inflam conversões no Ads.
       * Mapeamento GTM: docs/GTM_FUNNEL.md
       */
      trackEvent(ANALYTICS_EVENTS.START_TRIAL, startTrialPayload);
      toast.success("Conta criada! Faça login para continuar.");
      navigate("/signin", { replace: true });
    } catch (e: unknown) {
      toast.error(getAxiosErrorMessage(e));
    } finally {
      setSubmitting(false);
    }
  }

  const cardFocused =
    cardFocus === "" ? undefined : (cardFocus as "name" | "number" | "expiry" | "cvc");

  return (
    <>
      <PageMeta
        title="Criar conta | MarketChat"
        description="Cadastro trial 7 dias com cartão."
        noIndex
      />
      <AuthLayout>
        <div className="flex flex-col flex-1 w-full overflow-y-auto lg:w-1/2 no-scrollbar justify-center">
          <div className="w-full max-w-xl mx-auto py-10">
            <Link
              to="/signin"
              className="inline-flex items-center text-sm text-gray-500 transition-colors hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-300"
            >
              <ChevronLeftIcon className="size-5" />
              Voltar ao login
            </Link>

            <h1 className="mb-2 font-semibold text-gray-800 text-title-sm dark:text-white/90 sm:text-title-md">
              Criar sua conta
            </h1>
            <p className="text-sm text-gray-500 dark:text-gray-400 mb-6">
              Trial de {TRIAL_DAYS} dias. Cartão obrigatório para ativação.
            </p>

            <SignupProgressBar step={step} />

            <form
              onSubmit={(e) => {
                e.preventDefault();
                if (step === 3) void handleSubmit(submitRegister)();
              }}
            >
              {step === 1 && (
                <div className="space-y-5">
                  <div>
                    <Label>
                      Nome completo <span className="text-error-500">*</span>
                    </Label>
                    <Input placeholder="Maria Silva" {...register("fullName")} error={!!errors.fullName} />
                    {errors.fullName && (
                      <p className="mt-1 text-xs text-error-500">{errors.fullName.message}</p>
                    )}
                  </div>
                  <div>
                    <Label>
                      E-mail <span className="text-error-500">*</span>
                    </Label>
                    <Input type="email" placeholder="voce@empresa.com" {...register("email")} error={!!errors.email} />
                    {errors.email && <p className="mt-1 text-xs text-error-500">{errors.email.message}</p>}
                  </div>
                  <div>
                    <Label>
                      Senha <span className="text-error-500">*</span>
                    </Label>
                    <div className="relative">
                      <Input
                        type={showPassword ? "text" : "password"}
                        placeholder="Mínimo 8 caracteres"
                        {...register("password")}
                        error={!!errors.password}
                      />
                      <button
                        type="button"
                        onClick={() => setShowPassword(!showPassword)}
                        className="absolute z-30 -translate-y-1/2 cursor-pointer right-4 top-1/2"
                      >
                        {showPassword ? (
                          <EyeIcon className="fill-gray-500 dark:fill-gray-400 size-5" />
                        ) : (
                          <EyeCloseIcon className="fill-gray-500 dark:fill-gray-400 size-5" />
                        )}
                      </button>
                    </div>
                    <PasswordStrengthMeter password={password} />
                    {errors.password && (
                      <p className="mt-1 text-xs text-error-500">{errors.password.message}</p>
                    )}
                  </div>
                  <div>
                    <Controller
                      name="acceptTerms"
                      control={control}
                      render={({ field }) => (
                        <Checkbox
                          id="acceptTerms"
                          checked={field.value === true}
                          onChange={(checked) => field.onChange(checked ? true : false)}
                          label=""
                        />
                      )}
                    />
                    <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">
                      Li e concordo com a{" "}
                      <Link
                        to="/privacidade"
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-brand-600 hover:underline"
                      >
                        Política de Privacidade
                      </Link>{" "}
                      e os{" "}
                      <Link
                        to="/termos"
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-brand-600 hover:underline"
                      >
                        Termos de Uso
                      </Link>
                      . <span className="text-error-500">*</span>
                    </p>
                    {errors.acceptTerms && (
                      <p className="mt-1 text-xs text-error-500">{errors.acceptTerms.message}</p>
                    )}
                  </div>
                </div>
              )}

              {step === 2 && (
                <div className="space-y-5">
                  <div>
                    <Label>
                      Nome da empresa <span className="text-error-500">*</span>
                    </Label>
                    <Input
                      placeholder="Minha Empresa LTDA"
                      {...register("company_name")}
                      error={!!errors.company_name}
                    />
                    {errors.company_name && (
                      <p className="mt-1 text-xs text-error-500">{errors.company_name.message}</p>
                    )}
                  </div>
                  <div>
                    <Label>
                      CPF ou CNPJ <span className="text-error-500">*</span>
                    </Label>
                    <Controller
                      name="cpfCnpj"
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
                          onAccept={(value: string) => field.onChange(value)}
                          onBlur={field.onBlur}
                          inputRef={field.ref}
                          className={`h-11 w-full rounded-lg border bg-transparent px-4 py-2.5 text-sm shadow-theme-xs dark:text-white/90 ${
                            errors.cpfCnpj
                              ? "border-error-500 focus:border-error-500 focus:ring-error-500/20"
                              : "border-gray-300 dark:border-gray-700"
                          }`}
                          placeholder="00.00"
                        />
                      )}
                    />
                    {errors.cpfCnpj && <p className="mt-1 text-xs text-error-500">{errors.cpfCnpj.message}</p>}
                  </div>
                  <div>
                    <Label>
                      Telefone <span className="text-error-500">*</span>
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
                          className="h-11 w-full rounded-lg border border-gray-300 bg-transparent px-4 py-2.5 text-sm shadow-theme-xs dark:border-gray-700 dark:text-white/90"
                          placeholder="(11) 99999-9999"
                        />
                      )}
                    />
                    {errors.phone && <p className="mt-1 text-xs text-error-500">{errors.phone.message}</p>}
                  </div>
                  <div>
                    <Label>
                      CEP <span className="text-error-500">*</span>
                    </Label>
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
                          className="h-11 w-full rounded-lg border border-gray-300 bg-transparent px-4 py-2.5 text-sm dark:border-gray-700 dark:text-white/90"
                          placeholder="00000-000"
                        />
                      )}
                    />
                    {cepLoading && (
                      <div className="cep-loading-track mt-2" aria-busy="true" aria-label="Consultando CEP">
                        <div className="cep-loading-bar" />
                      </div>
                    )}
                    {errors.cep && <p className="mt-1 text-xs text-error-500">{errors.cep.message}</p>}
                  </div>
                  <div>
                    <Label>Endereço (logradouro / cidade)</Label>
                    <Input placeholder="Preencha após o CEP ou digite manualmente" {...register("address")} error={!!errors.address} />
                    {cepLookupFailed && (
                      <p className="mt-1 text-xs text-gray-600 dark:text-gray-400">
                        CEP não localizado na base dos Correios. Informe o endereço completo e escolha a UF abaixo.
                      </p>
                    )}
                    {errors.address && <p className="mt-1 text-xs text-error-500">{errors.address.message}</p>}
                  </div>
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <Label>
                        Número <span className="text-error-500">*</span>
                      </Label>
                      <Input {...register("addressNumber")} error={!!errors.addressNumber} />
                      {errors.addressNumber && (
                        <p className="mt-1 text-xs text-error-500">{errors.addressNumber.message}</p>
                      )}
                    </div>
                    <div>
                      <Label>Complemento</Label>
                      <Input {...register("complement")} />
                    </div>
                  </div>
                  <div>
                    <Label>
                      UF <span className="text-error-500">*</span>
                    </Label>
                    <Controller
                      name="province"
                      control={control}
                      render={({ field }) => (
                        <select
                          {...field}
                          className={`h-11 w-full appearance-none rounded-lg border bg-transparent bg-[length:1.25rem] bg-[right_0.75rem_center] bg-no-repeat px-4 py-2.5 text-sm shadow-theme-xs dark:text-white/90 ${
                            errors.province
                              ? "border-error-500 focus:border-error-500 focus:ring-error-500/20"
                              : "border-gray-300 dark:border-gray-700"
                          } dark:bg-gray-900`}
                          style={{
                            backgroundImage: `url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' fill='none' viewBox='0 0 24 24' stroke='%236b7280'%3E%3Cpath stroke-linecap='round' stroke-linejoin='round' stroke-width='2' d='M19 9l-7 7-7-7'%3E%3C/path%3E%3C/svg%3E")`,
                          }}
                        >
                          <option value="">Selecione a UF</option>
                          {UF_SELECT_OPTIONS.map((opt) => (
                            <option key={opt.value} value={opt.value}>
                              {opt.label}
                            </option>
                          ))}
                        </select>
                      )}
                    />
                    {errors.province && <p className="mt-1 text-xs text-error-500">{errors.province.message}</p>}
                  </div>
                </div>
              )}

              {step === 3 && (
                <div className="grid gap-8 lg:grid-cols-2 lg:items-start">
                  <div className="space-y-4">
                    <div className="flex justify-center lg:justify-start">
                      <Cards
                        number={digitsOnly(cardNumber)}
                        name={cardName}
                        expiry={cardExpiry}
                        cvc={cardCvv}
                        focused={cardFocused}
                        locale={{ valid: "Válido até" }}
                        placeholders={{ name: "NOME NO CARTÃO" }}
                      />
                    </div>
                    <div>
                      <Label>Número do cartão</Label>
                      <Controller
                        name="cardNumber"
                        control={control}
                        render={({ field }) => (
                          <IMaskInput
                            mask="0000 0000 0000 0000"
                            definitions={{ "0": /[0-9]/ }}
                            value={field.value}
                            unmask={false}
                            autoFocus
                            onAccept={(value: string) => field.onChange(value)}
                            onFocus={() => setCardFocus("number")}
                            onBlur={() => {
                              setCardFocus("");
                              field.onBlur();
                            }}
                            inputRef={field.ref}
                            className="h-11 w-full rounded-lg border border-gray-300 bg-transparent px-4 py-2.5 text-sm dark:border-gray-700 dark:text-white/90"
                            placeholder="0000 0000 0000 0000"
                          />
                        )}
                      />
                      {errors.cardNumber && (
                        <p className="mt-1 text-xs text-error-500">{errors.cardNumber.message}</p>
                      )}
                    </div>
                    <div>
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
                      {errors.cardName && <p className="mt-1 text-xs text-error-500">{errors.cardName.message}</p>}
                    </div>
                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <Label>Validade (MM/AA)</Label>
                        <Controller
                          name="cardExpiry"
                          control={control}
                          render={({ field }) => (
                            <IMaskInput
                              mask="00/00"
                              value={field.value}
                              unmask={false}
                              onAccept={(value: string) => field.onChange(value)}
                              onFocus={() => setCardFocus("expiry")}
                              onBlur={() => {
                                setCardFocus("");
                                field.onBlur();
                              }}
                              inputRef={field.ref}
                              className="h-11 w-full rounded-lg border border-gray-300 bg-transparent px-4 py-2.5 text-sm dark:border-gray-700 dark:text-white/90"
                              placeholder="MM/AA"
                            />
                          )}
                        />
                        {errors.cardExpiry && (
                          <p className="mt-1 text-xs text-error-500">{errors.cardExpiry.message}</p>
                        )}
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
                              onAccept={(value: string) => field.onChange(value)}
                              onFocus={() => setCardFocus("cvc")}
                              onBlur={() => {
                                setCardFocus("");
                                field.onBlur();
                              }}
                              inputRef={field.ref}
                              className="h-11 w-full rounded-lg border border-gray-300 bg-transparent px-4 py-2.5 text-sm dark:border-gray-700 dark:text-white/90"
                              placeholder="123"
                              type="password"
                            />
                          )}
                        />
                        {errors.cardCvv && <p className="mt-1 text-xs text-error-500">{errors.cardCvv.message}</p>}
                      </div>
                    </div>
                  </div>
                  <TrialSummaryCard trialDays={TRIAL_DAYS} />
                </div>
              )}

              <div className="flex flex-wrap gap-3 mt-8">
                {step > 1 && (
                  <Button type="button" variant="outline" onClick={goBack}>
                    Voltar
                  </Button>
                )}
                {step < 3 ? (
                  <Button type="button" onClick={() => void goNext()} disabled={!canContinueStep}>
                    Continuar
                  </Button>
                ) : (
                  <Button
                    type="submit"
                    disabled={submitting || !fullSignupSchema.safeParse(watchedValues).success}
                  >
                    {submitting ? "Enviando..." : "Finalizar cadastro"}
                  </Button>
                )}
              </div>
            </form>

            <p className="mt-6 text-sm text-center text-gray-500 dark:text-gray-400">
              Já tem conta?{" "}
              <Link to="/signin" className="text-brand-500 hover:text-brand-600 dark:text-brand-400">
                Entrar
              </Link>
            </p>
          </div>
        </div>
      </AuthLayout>
    </>
  );
}

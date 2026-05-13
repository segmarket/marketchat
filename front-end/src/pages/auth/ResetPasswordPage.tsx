import { useMemo, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { toast } from "sonner";
import { ChevronLeftIcon, EyeCloseIcon, EyeIcon } from "../../icons";
import Label from "../../components/form/Label";
import Input from "../../components/form/input/InputField";
import Button from "../../components/ui/button/Button";
import PageMeta from "../../components/common/PageMeta";
import AuthLayout from "../AuthPages/AuthPageLayout";
import { api } from "../../services/api";
import { getAxiosErrorMessage } from "../../utils/apiError";
import {
  passwordResetConfirmSchema,
  passwordResetRequestSchema,
  type PasswordResetConfirmValues,
  type PasswordResetRequestValues,
} from "../../features/auth/resetPasswordSchema";

const errOpts = {
  notAxiosMessage: "Não foi possível processar o pedido. Tente novamente.",
  genericHttpMessage: "Erro ao comunicar com o servidor. Tente novamente em instantes.",
};

export default function ResetPasswordPage() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const uid = searchParams.get("uid") ?? "";
  const token = searchParams.get("token") ?? "";
  const [showPassword, setShowPassword] = useState(false);
  const [showPassword2, setShowPassword2] = useState(false);

  const mode = useMemo(() => {
    if (uid && token) return "confirm" as const;
    if (uid || token) return "incomplete" as const;
    return "request" as const;
  }, [uid, token]);

  const requestForm = useForm<PasswordResetRequestValues>({
    resolver: zodResolver(passwordResetRequestSchema),
    defaultValues: { email: "" },
  });

  const confirmForm = useForm<PasswordResetConfirmValues>({
    resolver: zodResolver(passwordResetConfirmSchema),
    defaultValues: { new_password: "", new_password_confirm: "" },
  });

  async function onRequestSubmit(data: PasswordResetRequestValues) {
    try {
      await api.post("/api/auth/password/reset/", { email: data.email });
      toast.success("Se o e-mail existir em nossa base, você receberá instruções em instantes.");
      requestForm.reset();
    } catch (e) {
      toast.error(getAxiosErrorMessage(e, errOpts));
    }
  }

  async function onConfirmSubmit(data: PasswordResetConfirmValues) {
    try {
      await api.post("/api/auth/password/reset/confirm/", {
        uid,
        token,
        new_password: data.new_password,
      });
      toast.success("Senha atualizada. Você já pode entrar com a nova senha.");
      navigate("/login", { replace: true });
    } catch (e) {
      toast.error(getAxiosErrorMessage(e, errOpts));
    }
  }

  return (
    <>
      <PageMeta
        title="Recuperar senha | MarketChat"
        description="Redefina sua senha MarketChat com o link enviado por e-mail."
      />
      <AuthLayout>
        <div className="flex flex-col flex-1 w-full lg:w-1/2">
          <div className="w-full max-w-md pt-10 mx-auto">
            <Link
              to="/login"
              className="inline-flex items-center text-sm text-gray-500 transition-colors hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-300"
            >
              <ChevronLeftIcon className="size-5" />
              Voltar ao login
            </Link>
          </div>
          <div className="flex flex-col justify-center flex-1 w-full max-w-md mx-auto">
            {mode === "incomplete" && (
              <div>
                <h1 className="mb-2 font-semibold text-gray-800 text-title-sm dark:text-white/90 sm:text-title-md">
                  Link incompleto
                </h1>
                <p className="text-sm text-gray-500 dark:text-gray-400">
                  O link de recuperação precisa incluir os parâmetros <code className="text-xs">uid</code> e{" "}
                  <code className="text-xs">token</code>. Abra o link completo enviado por e-mail ou solicite um novo
                  pedido abaixo.
                </p>
                <div className="mt-6">
                  <Button
                    type="button"
                    size="sm"
                    variant="outline"
                    onClick={() => navigate("/reset-password", { replace: true })}
                  >
                    Solicitar novo e-mail
                  </Button>
                </div>
              </div>
            )}

            {mode === "request" && (
              <div>
                <div className="mb-5 sm:mb-8">
                  <h1 className="mb-2 font-semibold text-gray-800 text-title-sm dark:text-white/90 sm:text-title-md">
                    Esqueceu a senha?
                  </h1>
                  <p className="text-sm text-gray-500 dark:text-gray-400">
                    Informe o e-mail da sua conta. Se ele estiver cadastrado, enviaremos um link para definir uma nova
                    senha.
                  </p>
                </div>
                <form onSubmit={requestForm.handleSubmit(onRequestSubmit)} className="space-y-6">
                  <div>
                    <Label>
                      E-mail <span className="text-error-500">*</span>
                    </Label>
                    <Input
                      type="email"
                      placeholder="voce@empresa.com"
                      {...requestForm.register("email")}
                      error={!!requestForm.formState.errors.email}
                    />
                    {requestForm.formState.errors.email && (
                      <p className="mt-1 text-xs text-error-500">{requestForm.formState.errors.email.message}</p>
                    )}
                  </div>
                  <Button type="submit" className="w-full" size="sm" disabled={requestForm.formState.isSubmitting}>
                    {requestForm.formState.isSubmitting ? "Enviando..." : "Enviar link por e-mail"}
                  </Button>
                </form>
              </div>
            )}

            {mode === "confirm" && (
              <div>
                <div className="mb-5 sm:mb-8">
                  <h1 className="mb-2 font-semibold text-gray-800 text-title-sm dark:text-white/90 sm:text-title-md">
                    Nova senha
                  </h1>
                  <p className="text-sm text-gray-500 dark:text-gray-400">
                    Escolha uma senha forte. Ela substitui a senha anterior após confirmar.
                  </p>
                </div>
                <form onSubmit={confirmForm.handleSubmit(onConfirmSubmit)} className="space-y-6">
                  <div>
                    <Label>
                      Nova senha <span className="text-error-500">*</span>
                    </Label>
                    <div className="relative">
                      <Input
                        type={showPassword ? "text" : "password"}
                        placeholder="Mínimo 8 caracteres"
                        {...confirmForm.register("new_password")}
                        error={!!confirmForm.formState.errors.new_password}
                      />
                      <button
                        type="button"
                        onClick={() => setShowPassword(!showPassword)}
                        className="absolute z-30 -translate-y-1/2 cursor-pointer right-4 top-1/2"
                        aria-label={showPassword ? "Ocultar senha" : "Mostrar senha"}
                      >
                        {showPassword ? (
                          <EyeIcon className="fill-gray-500 dark:fill-gray-400 size-5" />
                        ) : (
                          <EyeCloseIcon className="fill-gray-500 dark:fill-gray-400 size-5" />
                        )}
                      </button>
                    </div>
                    {confirmForm.formState.errors.new_password && (
                      <p className="mt-1 text-xs text-error-500">{confirmForm.formState.errors.new_password.message}</p>
                    )}
                  </div>
                  <div>
                    <Label>
                      Confirmar senha <span className="text-error-500">*</span>
                    </Label>
                    <div className="relative">
                      <Input
                        type={showPassword2 ? "text" : "password"}
                        placeholder="Repita a nova senha"
                        {...confirmForm.register("new_password_confirm")}
                        error={!!confirmForm.formState.errors.new_password_confirm}
                      />
                      <button
                        type="button"
                        onClick={() => setShowPassword2(!showPassword2)}
                        className="absolute z-30 -translate-y-1/2 cursor-pointer right-4 top-1/2"
                        aria-label={showPassword2 ? "Ocultar confirmação" : "Mostrar confirmação"}
                      >
                        {showPassword2 ? (
                          <EyeIcon className="fill-gray-500 dark:fill-gray-400 size-5" />
                        ) : (
                          <EyeCloseIcon className="fill-gray-500 dark:fill-gray-400 size-5" />
                        )}
                      </button>
                    </div>
                    {confirmForm.formState.errors.new_password_confirm && (
                      <p className="mt-1 text-xs text-error-500">
                        {confirmForm.formState.errors.new_password_confirm.message}
                      </p>
                    )}
                  </div>
                  <Button type="submit" className="w-full" size="sm" disabled={confirmForm.formState.isSubmitting}>
                    {confirmForm.formState.isSubmitting ? "Salvando..." : "Salvar nova senha"}
                  </Button>
                </form>
              </div>
            )}
          </div>
        </div>
      </AuthLayout>
    </>
  );
}

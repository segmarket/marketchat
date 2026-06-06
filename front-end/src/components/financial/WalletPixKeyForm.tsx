import { useEffect, useState } from "react";
import { IMaskInput } from "react-imask";
import {
  MASK_INPUT_CLASS,
  pixKeyMaskForType,
  pixKeyPlaceholder,
} from "../../features/financial/pixKeyMask";
import { validatePixKey } from "../../features/financial/pixKeyValidation";
import type { PixKeyType } from "../../features/financial/types";
import Button from "../ui/button/Button";
import Input from "../form/input/InputField";
import Label from "../form/Label";

const PIX_KEY_TYPES: { value: PixKeyType; label: string }[] = [
  { value: "CPF", label: "CPF" },
  { value: "CNPJ", label: "CNPJ" },
  { value: "EMAIL", label: "E-mail" },
  { value: "PHONE", label: "Celular" },
  { value: "RANDOM", label: "Chave aleatória" },
];

type Props = {
  initialType?: PixKeyType;
  initialKey?: string;
  submitLabel?: string;
  showCancel?: boolean;
  onCancel?: () => void;
  onSubmit: (values: { pixKeyType: PixKeyType; pixKey: string }) => Promise<void>;
};

export default function WalletPixKeyForm({
  initialType = "EMAIL",
  initialKey = "",
  submitLabel = "Salvar conta",
  showCancel = false,
  onCancel,
  onSubmit,
}: Props) {
  const [pixKeyType, setPixKeyType] = useState<PixKeyType>(initialType);
  const [pixKey, setPixKey] = useState(initialKey);
  const [fieldError, setFieldError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    setPixKeyType(initialType);
    setPixKey(initialKey);
    setFieldError(null);
  }, [initialType, initialKey]);

  function handleTypeChange(nextType: PixKeyType) {
    setPixKeyType(nextType);
    setPixKey("");
    setFieldError(null);
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const error = validatePixKey(pixKeyType, pixKey);
    if (error) {
      setFieldError(error);
      return;
    }

    setFieldError(null);
    setSubmitting(true);
    try {
      await onSubmit({ pixKeyType, pixKey: pixKey.trim() });
    } finally {
      setSubmitting(false);
    }
  }

  const maskConfig = pixKeyMaskForType(pixKeyType);
  const selectClassName =
    "h-11 w-full rounded-lg border border-gray-300 bg-transparent px-4 text-sm text-gray-800 shadow-theme-xs focus:border-brand-300 focus:outline-hidden focus:ring-3 focus:ring-brand-500/10 dark:border-gray-700 dark:bg-gray-900 dark:text-white/90";

  return (
    <form onSubmit={handleSubmit} className="grid grid-cols-1 gap-4 md:grid-cols-2">
      <div>
        <Label>Tipo de chave Pix</Label>
        <select
          className={selectClassName}
          value={pixKeyType}
          onChange={(e) => handleTypeChange(e.target.value as PixKeyType)}
        >
          {PIX_KEY_TYPES.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
      </div>
      <div>
        <Label>Chave Pix</Label>
        {maskConfig.mask ? (
          <IMaskInput
            key={pixKeyType}
            mask={maskConfig.mask}
            value={pixKey}
            unmask={false}
            onAccept={(value: string) => {
              setPixKey(value);
              if (fieldError) setFieldError(null);
            }}
            className={MASK_INPUT_CLASS}
            placeholder={pixKeyPlaceholder(pixKeyType)}
          />
        ) : (
          <Input
            type={pixKeyType === "EMAIL" ? "email" : "text"}
            placeholder={pixKeyPlaceholder(pixKeyType)}
            value={pixKey}
            onChange={(e) => {
              setPixKey(e.target.value);
              if (fieldError) setFieldError(null);
            }}
          />
        )}
        {fieldError ? <p className="mt-1 text-sm text-red-500">{fieldError}</p> : null}
      </div>
      <div className="md:col-span-2 flex justify-end gap-3">
        {showCancel && onCancel ? (
          <Button type="button" variant="outline" onClick={onCancel} disabled={submitting}>
            Cancelar
          </Button>
        ) : null}
        <Button type="submit" disabled={submitting || !pixKey.trim()}>
          {submitting ? "Salvando…" : submitLabel}
        </Button>
      </div>
    </form>
  );
}

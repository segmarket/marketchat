import { digitsOnly, isValidCNPJ, isValidCPF } from "../../utils/cpfCnpj";
import type { PixKeyType } from "./types";

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export function validatePixKey(type: PixKeyType, raw: string): string | null {
  const value = raw.trim();
  if (!value) {
    return "Informe a chave Pix.";
  }

  switch (type) {
    case "CPF": {
      const digits = digitsOnly(value);
      if (digits.length !== 11 || !isValidCPF(digits)) {
        return "Formato de CPF inválido.";
      }
      return null;
    }
    case "CNPJ": {
      const digits = digitsOnly(value);
      if (digits.length !== 14 || !isValidCNPJ(digits)) {
        return "Formato de CNPJ inválido.";
      }
      return null;
    }
    case "PHONE": {
      const digits = digitsOnly(value);
      if (digits.length < 10 || digits.length > 11) {
        return "Formato de celular inválido.";
      }
      return null;
    }
    case "EMAIL": {
      if (!EMAIL_RE.test(value)) {
        return "Formato de e-mail inválido.";
      }
      return null;
    }
    case "RANDOM": {
      if (value.length < 8) {
        return "Chave aleatória inválida.";
      }
      return null;
    }
    default:
      return "Chave Pix inválida para o tipo selecionado.";
  }
}

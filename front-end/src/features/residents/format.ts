export function digitsOnly(value: string): string {
  return value.replace(/\D/g, "");
}

/** Exibição na tabela e modal (suporta DDI 55). */
export function formatPhoneBR(phone: string): string {
  const digits = digitsOnly(phone);
  if (!digits) return "";

  let local = digits;
  if (local.startsWith("55") && local.length >= 12) {
    local = local.slice(2);
  }
  if (local.length === 11) {
    return `+55 (${local.slice(0, 2)}) ${local.slice(2, 7)}-${local.slice(7)}`;
  }
  if (local.length === 10) {
    return `+55 (${local.slice(0, 2)}) ${local.slice(2, 6)}-${local.slice(6)}`;
  }
  if (digits.length > 6) {
    return `+${digits}`;
  }
  return digits;
}

/** Máscara progressiva para campo de busca (até 13 dígitos com DDI). */
export function maskPhoneInput(value: string): string {
  const digits = digitsOnly(value).slice(0, 13);
  if (!digits) return "";

  let prefix = "";
  let local = digits;
  if (digits.startsWith("55") && digits.length > 2) {
    prefix = "+55 ";
    local = digits.slice(2);
  }

  if (local.length <= 2) {
    return `${prefix}(${local}`;
  }
  if (local.length <= 6) {
    return `${prefix}(${local.slice(0, 2)}) ${local.slice(2)}`;
  }
  if (local.length <= 10) {
    return `${prefix}(${local.slice(0, 2)}) ${local.slice(2, 6)}-${local.slice(6)}`;
  }
  return `${prefix}(${local.slice(0, 2)}) ${local.slice(2, 7)}-${local.slice(7, 11)}`;
}

export function formatDateBR(iso: string): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso;
  return new Intl.DateTimeFormat("pt-BR", {
    dateStyle: "short",
    timeStyle: "short",
  }).format(date);
}

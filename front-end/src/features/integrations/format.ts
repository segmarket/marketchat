const DEFAULT_AVATAR = "/images/user/user-01.jpg";

export function formatPhoneBR(phoneOrJid: string): string {
  const digits = phoneOrJid.replace(/\D/g, "");
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

export function resolveProfileAvatar(url: string): string {
  return url?.trim() ? url.trim() : DEFAULT_AVATAR;
}

export function platformLabel(platform: string): string {
  if (platform === "android") return "Android";
  if (platform === "ios") return "iOS";
  return "Desconhecido";
}

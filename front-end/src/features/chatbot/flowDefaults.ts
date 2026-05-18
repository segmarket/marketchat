import type { AccountSettingsResponse } from "../settings/types";
import type { FlowData, FlowNode } from "./types";

export function digitsOnlyPhone(value: string): string {
  return value.replace(/\D/g, "");
}

/** Telefone do dono: empresa (tenant) ou, se vazio, telefone pessoal do usuário logado. */
export function resolveAccountOwnerPhone(account: AccountSettingsResponse): string {
  const tenantPhone = digitsOnlyPhone(account.tenant?.phone ?? "");
  if (tenantPhone) return tenantPhone;
  return digitsOnlyPhone(account.user.phone ?? "");
}

/**
 * Preenche ownerPhone nos nós de alerta.
 * @param force — se true, substitui sempre (ex.: ao carregar template pronto).
 */
export function applyDefaultOwnerPhone(
  flow: FlowData,
  defaultOwnerPhone: string,
  force = false,
): FlowData {
  const phone = digitsOnlyPhone(defaultOwnerPhone);
  if (!phone) return flow;

  const nodes = (flow.nodes ?? []).map((node) => {
    if (node.type !== "owner_alert") return node;
    const data = node.data as { ownerPhone?: string };
    if (!force && data.ownerPhone && digitsOnlyPhone(data.ownerPhone)) return node;
    return {
      ...node,
      data: { ...data, ownerPhone: phone },
    } as FlowNode;
  });

  return { ...flow, nodes };
}

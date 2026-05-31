import { useState } from "react";
import { toast } from "sonner";
import { syncPixAccountStatus } from "../../../features/integrations/pix/api";
import type { AccountStatus, AsaasKycStatus, PixConfig } from "../../../features/integrations/pix/types";
import { getAxiosErrorMessage } from "../../../utils/apiError";
import { CheckCircleIcon } from "../../../icons";
import Badge from "../../ui/badge/Badge";
import Button from "../../ui/button/Button";

type Props = {
  config: PixConfig;
  onSynced: (config: PixConfig) => void;
};

function kycLabel(value: AsaasKycStatus | undefined): string {
  const v = (value || "").toUpperCase();
  if (!v || v === "NOT_SENT") return "—";
  if (v === "APPROVED") return "Aprovado";
  if (v === "REJECTED") return "Rejeitado";
  if (v === "AWAITING_APPROVAL") return "Em análise";
  if (v === "PENDING") return "Pendente";
  return v.replace(/_/g, " ").toLowerCase();
}

function statusBadge(accountStatus: AccountStatus, splitReady: boolean) {
  if (splitReady || accountStatus === "APPROVED") {
    return (
      <Badge color="success" size="md" variant="solid" startIcon={<CheckCircleIcon className="size-4" />}>
        Split Pix ativo (subconta aprovada)
      </Badge>
    );
  }
  if (accountStatus === "REJECTED") {
    return (
      <Badge color="error" size="md" variant="solid">
        Conta rejeitada pelo Asaas
      </Badge>
    );
  }
  return (
    <Badge color="warning" size="md" variant="solid">
      Em análise pelo Asaas
    </Badge>
  );
}

export default function PixAccountStatusCard({ config, onSynced }: Props) {
  const [syncing, setSyncing] = useState(false);

  if (!config.has_wallet) return null;

  const splitReady = Boolean(config.split_ready);

  async function handleSync() {
    setSyncing(true);
    try {
      const updated = await syncPixAccountStatus();
      onSynced(updated);
      toast.success("Status atualizado com o Asaas.");
    } catch (err) {
      toast.error(
        getAxiosErrorMessage(err, {
          notAxiosMessage: "Não foi possível sincronizar o status com o Asaas.",
        }),
      );
    } finally {
      setSyncing(false);
    }
  }

  return (
    <div className="rounded-xl border border-gray-200 bg-gray-50 p-4 dark:border-gray-800 dark:bg-white/[0.03]">
      <p className="mb-3 text-sm font-medium text-gray-800 dark:text-white/90">Status da subconta (Asaas)</p>

      <div className="mb-3">{statusBadge(config.account_status, splitReady)}</div>

      {!splitReady ? (
        <p className="mb-3 text-xs leading-relaxed text-gray-600 dark:text-gray-400">
          O Pix do morador só fará split 100% para sua subconta após aprovação geral no Asaas. Os dados
          enviados (CNPJ, endereço do mercado, faturamento) devem coincidir com o cadastro comercial.
        </p>
      ) : null}

      {config.status_message ? (
        <p className="mb-3 text-xs text-gray-600 dark:text-gray-400">{config.status_message}</p>
      ) : null}

      <dl className="mb-4 space-y-1.5 text-xs text-gray-600 dark:text-gray-400">
        <div className="flex justify-between gap-2">
          <dt>Geral</dt>
          <dd className="font-medium text-gray-800 dark:text-gray-200">
            {kycLabel(config.asaas_status_general)}
          </dd>
        </div>
        <div className="flex justify-between gap-2">
          <dt>Dados comerciais</dt>
          <dd className="font-medium text-gray-800 dark:text-gray-200">
            {kycLabel(config.asaas_status_commercial)}
          </dd>
        </div>
        <div className="flex justify-between gap-2">
          <dt>Documentação</dt>
          <dd className="font-medium text-gray-800 dark:text-gray-200">
            {kycLabel(config.asaas_status_documentation)}
          </dd>
        </div>
        <div className="flex justify-between gap-2">
          <dt>Conta bancária</dt>
          <dd className="font-medium text-gray-800 dark:text-gray-200">
            {kycLabel(config.asaas_status_bank)}
          </dd>
        </div>
      </dl>

      {config.can_sync_status && config.can_manage ? (
        <Button type="button" size="sm" variant="outline" disabled={syncing} onClick={() => void handleSync()}>
          {syncing ? "Consultando…" : "Atualizar status no Asaas"}
        </Button>
      ) : null}

      {config.status_synced_at ? (
        <p className="mt-2 text-[10px] text-gray-500 dark:text-gray-500">
          Última sync: {new Date(config.status_synced_at).toLocaleString("pt-BR")}
        </p>
      ) : null}
    </div>
  );
}

import { CheckCircleIcon } from "../../../icons";
import Badge from "../../ui/badge/Badge";
import type { AccountStatus } from "../../../features/integrations/pix/types";

type Props = {
  hasWallet: boolean;
  accountStatus: AccountStatus;
};

export default function PixAccountStatusCard({ hasWallet, accountStatus }: Props) {
  if (!hasWallet) return null;

  const isApproved = accountStatus === "APPROVED";

  return (
    <div className="rounded-xl border border-gray-200 bg-gray-50 p-4 dark:border-gray-800 dark:bg-white/[0.03]">
      <p className="mb-3 text-sm font-medium text-gray-800 dark:text-white/90">Status da conta</p>
      {isApproved ? (
        <Badge color="success" size="md" variant="solid" startIcon={<CheckCircleIcon className="size-4" />}>
          Conta de Recebimento Ativa
        </Badge>
      ) : accountStatus === "REJECTED" ? (
        <Badge color="error" size="md" variant="solid">
          Conta rejeitada pelo Asaas
        </Badge>
      ) : (
        <Badge color="warning" size="md" variant="solid">
          Em Análise pelo Asaas
        </Badge>
      )}
    </div>
  );
}

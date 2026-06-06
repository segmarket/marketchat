import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";
import { fetchFinancialStatement } from "../../features/financial/api";
import type { FinancialStatement } from "../../features/financial/types";
import { getAxiosErrorMessage } from "../../utils/apiError";
import FinancialStatementTable from "./FinancialStatementTable";
import FinancialSummaryCards from "./FinancialSummaryCards";
import WalletPixSettingsCard from "./WalletPixSettingsCard";
import WithdrawModal from "./WithdrawModal";

export default function FinancialPanel() {
  const [page, setPage] = useState(1);
  const [statement, setStatement] = useState<FinancialStatement | null>(null);
  const [loading, setLoading] = useState(true);
  const [withdrawOpen, setWithdrawOpen] = useState(false);

  const loadStatement = useCallback(async (targetPage: number) => {
    setLoading(true);
    try {
      const data = await fetchFinancialStatement(targetPage);
      setStatement(data);
    } catch (err) {
      toast.error(
        getAxiosErrorMessage(err, {
          notAxiosMessage: "Não foi possível carregar o extrato financeiro.",
        }),
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadStatement(page);
  }, [loadStatement, page]);

  function handleWithdrawSuccess() {
    setPage(1);
    void loadStatement(1);
  }

  const canWithdraw = Boolean(statement?.has_pix_key_configured);

  return (
    <>
      {!statement?.has_pix_key_configured ? (
        <WalletPixSettingsCard onSaved={() => void loadStatement(page)} />
      ) : null}

      <FinancialSummaryCards
        balanceAvailable={statement?.balance_available ?? "0"}
        balanceProcessing={statement?.balance_processing ?? "0"}
        loading={loading && !statement}
        canWithdraw={canWithdraw}
        onWithdrawClick={() => {
          if (canWithdraw) setWithdrawOpen(true);
        }}
      />

      <FinancialStatementTable
        rows={statement?.results ?? []}
        loading={loading && !statement}
        page={statement?.page ?? page}
        nextPage={statement?.next ?? null}
        prevPage={statement?.previous ?? null}
        totalCount={statement?.total_count ?? 0}
        onPageChange={setPage}
      />

      <WithdrawModal
        open={withdrawOpen}
        balanceAvailable={statement?.balance_available ?? "0"}
        defaultPixKey={statement?.default_pix_key ?? ""}
        defaultPixKeyType={statement?.default_pix_key_type ?? ""}
        onClose={() => setWithdrawOpen(false)}
        onSuccess={handleWithdrawSuccess}
      />
    </>
  );
}

import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";
import PageBreadcrumb from "../../components/common/PageBreadCrumb";
import PageMeta from "../../components/common/PageMeta";
import FormContentCard from "../../components/layout/FormContentCard";
import FormPageLayout from "../../components/layout/FormPageLayout";
import MarketDeleteConfirmModal from "../../components/markets/MarketDeleteConfirmModal";
import MarketFormModal from "../../components/markets/MarketFormModal";
import MarketsSearchPanel from "../../components/markets/MarketsSearchPanel";
import MarketsTable from "../../components/markets/MarketsTable";
import Button from "../../components/ui/button/Button";
import { buildMarketsQueryParams, deleteMarket, fetchMarkets } from "../../features/markets/api";
import {
  emptyMarketsSearchFilters,
  hasActiveMarketsFilters,
  type MarketsSearchFilters,
} from "../../features/markets/searchTypes";
import type { Market } from "../../features/markets/types";
import { getAxiosErrorMessage } from "../../utils/apiError";

export default function MarketsPage() {
  const [markets, setMarkets] = useState<Market[]>([]);
  const [loading, setLoading] = useState(true);
  const [appliedFilters, setAppliedFilters] = useState<MarketsSearchFilters>(
    emptyMarketsSearchFilters(),
  );
  const [formOpen, setFormOpen] = useState(false);
  const [formMode, setFormMode] = useState<"create" | "edit">("create");
  const [editingMarket, setEditingMarket] = useState<Market | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<Market | null>(null);
  const [deleteBusy, setDeleteBusy] = useState(false);

  const loadMarkets = useCallback(async (filters: MarketsSearchFilters) => {
    setLoading(true);
    try {
      const params = buildMarketsQueryParams(filters);
      const data = await fetchMarkets(params);
      setMarkets(data);
    } catch (err) {
      toast.error(getAxiosErrorMessage(err, { notAxiosMessage: "Não foi possível carregar mercados." }));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadMarkets(appliedFilters);
  }, [appliedFilters, loadMarkets]);

  function openCreateModal() {
    setFormMode("create");
    setEditingMarket(null);
    setFormOpen(true);
  }

  function openEditModal(market: Market) {
    setFormMode("edit");
    setEditingMarket(market);
    setFormOpen(true);
  }

  function closeFormModal() {
    setFormOpen(false);
    setEditingMarket(null);
  }

  function closeDeleteModal() {
    if (deleteBusy) return;
    setDeleteTarget(null);
  }

  async function handleConfirmDelete() {
    if (!deleteTarget) return;
    setDeleteBusy(true);
    try {
      await deleteMarket(deleteTarget.id);
      toast.success("Mercado removido com sucesso.");
      setDeleteTarget(null);
      await loadMarkets(appliedFilters);
    } catch (err) {
      toast.error(getAxiosErrorMessage(err, { notAxiosMessage: "Falha ao remover mercado." }));
    } finally {
      setDeleteBusy(false);
    }
  }

  const filtersActive = hasActiveMarketsFilters(appliedFilters);

  return (
    <>
      <PageMeta title="Meus Mercados | MarketChat" description="Gerenciamento de mercados" />
      <FormPageLayout>
        <PageBreadcrumb pageTitle="Meus Mercados" />

        <FormContentCard>
        <div className="mb-4 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <p className="text-sm text-gray-500 dark:text-gray-400">
            Cadastre e gerencie seus mercados
          </p>
          <Button onClick={openCreateModal}>+ Adicionar Novo Mercado</Button>
        </div>

        <MarketsSearchPanel
          busy={loading}
          resultCount={loading ? undefined : markets.length}
          onSearch={setAppliedFilters}
          onClear={() => setAppliedFilters(emptyMarketsSearchFilters())}
        />

        <MarketsTable
          markets={markets}
          loading={loading}
          filtersActive={filtersActive}
          onEdit={openEditModal}
          onDelete={setDeleteTarget}
        />
        </FormContentCard>
      </FormPageLayout>

      <MarketFormModal
        isOpen={formOpen}
        mode={formMode}
        market={editingMarket}
        onClose={closeFormModal}
        onSaved={() => void loadMarkets(appliedFilters)}
      />

      <MarketDeleteConfirmModal
        isOpen={deleteTarget !== null}
        busy={deleteBusy}
        marketName={deleteTarget?.name}
        onClose={closeDeleteModal}
        onConfirm={() => void handleConfirmDelete()}
      />
    </>
  );
}

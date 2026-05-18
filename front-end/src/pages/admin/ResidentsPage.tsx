import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";
import PageBreadcrumb from "../../components/common/PageBreadCrumb";
import PageMeta from "../../components/common/PageMeta";
import ResidentEditModal from "../../components/residents/ResidentEditModal";
import ResidentsSearchPanel from "../../components/residents/ResidentsSearchPanel";
import ResidentsTable from "../../components/residents/ResidentsTable";
import {
  buildResidentsQueryParams,
  fetchResidentMarkets,
  fetchResidents,
  patchResidentMarket,
} from "../../features/residents/api";
import type { ResidentEditFormValues } from "../../features/residents/schemas";
import {
  emptyResidentsSearchFilters,
  hasActiveResidentsFilters,
  type ResidentsSearchFilters,
} from "../../features/residents/searchTypes";
import type { Resident, ResidentMarketOption } from "../../features/residents/types";
import { getAxiosErrorMessage } from "../../utils/apiError";

export default function ResidentsPage() {
  const [residents, setResidents] = useState<Resident[]>([]);
  const [markets, setMarkets] = useState<ResidentMarketOption[]>([]);
  const [loading, setLoading] = useState(true);
  const [appliedFilters, setAppliedFilters] = useState<ResidentsSearchFilters>(
    emptyResidentsSearchFilters,
  );
  const [editingResident, setEditingResident] = useState<Resident | null>(null);
  const [editBusy, setEditBusy] = useState(false);

  const loadResidents = useCallback(async (filters: ResidentsSearchFilters) => {
    setLoading(true);
    try {
      const params = buildResidentsQueryParams(filters);
      const data = await fetchResidents(params);
      setResidents(data);
    } catch (err) {
      toast.error(getAxiosErrorMessage(err, { notAxiosMessage: "Não foi possível carregar moradores." }));
    } finally {
      setLoading(false);
    }
  }, []);

  const loadMarkets = useCallback(async () => {
    try {
      const data = await fetchResidentMarkets();
      setMarkets(data);
    } catch (err) {
      toast.error(getAxiosErrorMessage(err, { notAxiosMessage: "Não foi possível carregar mercados." }));
    }
  }, []);

  useEffect(() => {
    void loadMarkets();
  }, [loadMarkets]);

  useEffect(() => {
    void loadResidents(appliedFilters);
  }, [appliedFilters, loadResidents]);

  function handleSearch(filters: ResidentsSearchFilters) {
    setAppliedFilters(filters);
  }

  function handleClearSearch() {
    setAppliedFilters(emptyResidentsSearchFilters());
  }

  async function handleEditSubmit(values: ResidentEditFormValues) {
    if (!editingResident) return;
    const marketId = Number.parseInt(values.market_id, 10);
    if (!Number.isFinite(marketId) || marketId <= 0) return;
    setEditBusy(true);
    try {
      await patchResidentMarket(editingResident.id, marketId);
      toast.success("Morador atualizado.");
      setEditingResident(null);
      await loadResidents(appliedFilters);
    } catch (err) {
      toast.error(getAxiosErrorMessage(err, { notAxiosMessage: "Falha ao atualizar morador." }));
    } finally {
      setEditBusy(false);
    }
  }

  const filtersActive = hasActiveResidentsFilters(appliedFilters);

  return (
    <>
      <PageMeta title="Moradores | MarketChat" description="Moradores cadastrados via WhatsApp" />
      <PageBreadcrumb pageTitle="Moradores" />

      <div className="rounded-2xl border border-gray-200 bg-white p-5 dark:border-gray-800 dark:bg-white/[0.03] md:p-6">
        <p className="mb-4 text-sm text-gray-500 dark:text-gray-400">
          Moradores que concluíram o cadastro pelo WhatsApp.
        </p>

        <ResidentsSearchPanel
          markets={markets}
          busy={loading}
          resultCount={loading ? undefined : residents.length}
          onSearch={handleSearch}
          onClear={handleClearSearch}
        />

        <ResidentsTable
          residents={residents}
          loading={loading}
          filtersActive={filtersActive}
          onEdit={setEditingResident}
        />
      </div>

      <ResidentEditModal
        resident={editingResident}
        markets={markets}
        isOpen={editingResident !== null}
        busy={editBusy}
        onClose={() => setEditingResident(null)}
        onSubmit={(values) => void handleEditSubmit(values)}
      />
    </>
  );
}

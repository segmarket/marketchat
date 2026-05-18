import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";
import AdminPageLayout from "../../components/layout/AdminPageShell";
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
      <AdminPageLayout
        pageTitle="Moradores"
        metaDescription="Moradores cadastrados via WhatsApp"
        description="Moradores que concluíram o cadastro pelo WhatsApp."
      >
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
      </AdminPageLayout>

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

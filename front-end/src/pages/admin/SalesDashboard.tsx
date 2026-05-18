import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";
import AdminPageLayout from "../../components/layout/AdminPageShell";
import OrderDetailsModal from "../../components/sales/OrderDetailsModal";
import SalesFilterBar from "../../components/sales/SalesFilterBar";
import SalesKpiBar from "../../components/sales/SalesKpiBar";
import SalesOrdersTable from "../../components/sales/SalesOrdersTable";
import Button from "../../components/ui/button/Button";
import { fetchCartDetail, fetchSalesDashboard } from "../../features/sales/api";
import {
  buildSalesQueryParams,
  emptySalesSearchFilters,
  hasActiveSalesFilters,
  type SalesSearchFilters,
} from "../../features/sales/searchTypes";
import type {
  CartDetail,
  SalesMarketOption,
  SalesMetrics,
  SalesOrderRow,
} from "../../features/sales/types";
import { fetchResidentMarkets } from "../../features/residents/api";
import { getAxiosErrorMessage } from "../../utils/apiError";

export default function SalesDashboard() {
  const [filters, setFilters] = useState<SalesSearchFilters>(emptySalesSearchFilters());
  const [debouncedFilters, setDebouncedFilters] = useState(filters);
  const [page, setPage] = useState(1);
  const [metrics, setMetrics] = useState<SalesMetrics | null>(null);
  const [rows, setRows] = useState<SalesOrderRow[]>([]);
  const [totalCount, setTotalCount] = useState(0);
  const [nextPage, setNextPage] = useState<number | null>(null);
  const [prevPage, setPrevPage] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [markets, setMarkets] = useState<SalesMarketOption[]>([]);

  const [detailModalOpen, setDetailModalOpen] = useState(false);
  const [detailLoading, setDetailLoading] = useState(false);
  const [selectedCart, setSelectedCart] = useState<CartDetail | null>(null);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      setDebouncedFilters((prev) => {
        if (prev.residentName === filters.residentName) return prev;
        setPage(1);
        return { ...prev, residentName: filters.residentName };
      });
    }, 300);
    return () => window.clearTimeout(timer);
  }, [filters.residentName]);

  useEffect(() => {
    setDebouncedFilters((prev) => {
      if (
        prev.marketId === filters.marketId
        && prev.status === filters.status
        && prev.dateFrom === filters.dateFrom
        && prev.dateTo === filters.dateTo
      ) {
        return prev;
      }
      setPage(1);
      return {
        ...prev,
        marketId: filters.marketId,
        status: filters.status,
        dateFrom: filters.dateFrom,
        dateTo: filters.dateTo,
      };
    });
  }, [filters.marketId, filters.status, filters.dateFrom, filters.dateTo]);

  const loadMarkets = useCallback(async () => {
    try {
      const data = await fetchResidentMarkets();
      setMarkets(data);
    } catch (err) {
      toast.error(
        getAxiosErrorMessage(err, { notAxiosMessage: "Não foi possível carregar condomínios." }),
      );
    }
  }, []);

  const loadDashboard = useCallback(async () => {
    setLoading(true);
    try {
      const params = buildSalesQueryParams(debouncedFilters, page);
      const data = await fetchSalesDashboard(params);
      setMetrics(data.metrics);
      setRows(data.orders.results);
      setTotalCount(data.orders.count);
      setNextPage(data.orders.next);
      setPrevPage(data.orders.previous);
    } catch (err) {
      toast.error(
        getAxiosErrorMessage(err, { notAxiosMessage: "Não foi possível carregar vendas." }),
      );
    } finally {
      setLoading(false);
    }
  }, [debouncedFilters, page]);

  useEffect(() => {
    void loadMarkets();
  }, [loadMarkets]);

  useEffect(() => {
    void loadDashboard();
  }, [loadDashboard]);

  async function handleViewDetail(row: SalesOrderRow) {
    setDetailModalOpen(true);
    setDetailLoading(true);
    setSelectedCart(null);
    try {
      const detail = await fetchCartDetail(row.id);
      setSelectedCart(detail);
    } catch (err) {
      toast.error(
        getAxiosErrorMessage(err, { notAxiosMessage: "Não foi possível carregar o pedido." }),
      );
      setDetailModalOpen(false);
    } finally {
      setDetailLoading(false);
    }
  }

  function handleClearFilters() {
    const empty = emptySalesSearchFilters();
    setFilters(empty);
    setDebouncedFilters(empty);
    setPage(1);
  }

  const filtersActive = hasActiveSalesFilters(debouncedFilters);
  const pageSize = 20;
  const totalPages = Math.max(1, Math.ceil(totalCount / pageSize));

  return (
    <>
      <AdminPageLayout
        pageTitle="Painel de Vendas"
        metaDescription="Monitoramento de vendas e auditoria"
        description="Acompanhe faturamento, pedidos e fotos de segurança enviadas pelo WhatsApp antes do pagamento."
      >
        <SalesKpiBar metrics={metrics} loading={loading} />

        <SalesFilterBar
          filters={filters}
          markets={markets}
          busy={loading}
          onChange={setFilters}
          onClear={handleClearFilters}
        />

        <SalesOrdersTable
          rows={rows}
          loading={loading}
          filtersActive={filtersActive}
          onViewDetail={handleViewDetail}
        />

        {!loading && totalCount > 0 ? (
          <div className="mt-6 flex flex-col items-center justify-between gap-3 sm:flex-row">
            <p className="text-sm text-gray-500">
              Página {page} de {totalPages} · {totalCount} pedido
              {totalCount === 1 ? "" : "s"}
            </p>
            <div className="flex gap-2">
              <Button
                type="button"
                size="sm"
                variant="outline"
                disabled={!prevPage}
                onClick={() => setPage((p) => Math.max(1, p - 1))}
              >
                Anterior
              </Button>
              <Button
                type="button"
                size="sm"
                variant="outline"
                disabled={!nextPage}
                onClick={() => setPage((p) => p + 1)}
              >
                Próxima
              </Button>
            </div>
          </div>
        ) : null}
      </AdminPageLayout>

      <OrderDetailsModal
        open={detailModalOpen}
        loading={detailLoading}
        cart={selectedCart}
        onClose={() => setDetailModalOpen(false)}
      />
    </>
  );
}

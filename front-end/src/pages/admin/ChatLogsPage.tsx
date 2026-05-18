import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";
import AdminPageLayout from "../../components/layout/AdminPageShell";
import ChatConversationDrawer from "../../components/chatLogs/ChatConversationDrawer";
import ChatLogsFilterBar from "../../components/chatLogs/ChatLogsFilterBar";
import ChatLogsTable from "../../components/chatLogs/ChatLogsTable";
import Button from "../../components/ui/button/Button";
import { fetchChatLogs, fetchConversation } from "../../features/chatLogs/api";
import {
  buildChatLogsQueryParams,
  emptyChatLogsSearchFilters,
  hasActiveChatLogsFilters,
  type ChatLogsSearchFilters,
} from "../../features/chatLogs/searchTypes";
import type {
  ChatAttendanceRow,
  ChatConversationResponse,
  ChatLogsMarketOption,
} from "../../features/chatLogs/types";
import { fetchResidentMarkets } from "../../features/residents/api";
import { getAxiosErrorMessage } from "../../utils/apiError";

export default function ChatLogsPage() {
  const [filters, setFilters] = useState<ChatLogsSearchFilters>(emptyChatLogsSearchFilters);
  const [debouncedFilters, setDebouncedFilters] = useState(filters);
  const [page, setPage] = useState(1);
  const [rows, setRows] = useState<ChatAttendanceRow[]>([]);
  const [totalCount, setTotalCount] = useState(0);
  const [nextPage, setNextPage] = useState<number | null>(null);
  const [prevPage, setPrevPage] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [markets, setMarkets] = useState<ChatLogsMarketOption[]>([]);

  const [drawerOpen, setDrawerOpen] = useState(false);
  const [drawerLoading, setDrawerLoading] = useState(false);
  const [conversation, setConversation] = useState<ChatConversationResponse | null>(null);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      setDebouncedFilters((prev) => {
        if (
          prev.residentName === filters.residentName
          && prev.phone === filters.phone
        ) {
          return prev;
        }
        setPage(1);
        return { ...prev, residentName: filters.residentName, phone: filters.phone };
      });
    }, 300);
    return () => window.clearTimeout(timer);
  }, [filters.residentName, filters.phone]);

  useEffect(() => {
    setDebouncedFilters((prev) => {
      if (
        prev.marketId === filters.marketId
        && prev.intentType === filters.intentType
        && prev.date === filters.date
      ) {
        return prev;
      }
      setPage(1);
      return {
        ...prev,
        marketId: filters.marketId,
        intentType: filters.intentType,
        date: filters.date,
      };
    });
  }, [filters.marketId, filters.intentType, filters.date]);

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

  const loadLogs = useCallback(async () => {
    setLoading(true);
    try {
      const params = buildChatLogsQueryParams(debouncedFilters, page);
      const data = await fetchChatLogs(params);
      setRows(data.results);
      setTotalCount(data.count);
      setNextPage(data.next);
      setPrevPage(data.previous);
    } catch (err) {
      toast.error(
        getAxiosErrorMessage(err, { notAxiosMessage: "Não foi possível carregar atendimentos." }),
      );
    } finally {
      setLoading(false);
    }
  }, [debouncedFilters, page]);

  useEffect(() => {
    void loadMarkets();
  }, [loadMarkets]);

  useEffect(() => {
    void loadLogs();
  }, [loadLogs]);

  async function handleViewConversation(row: ChatAttendanceRow) {
    setDrawerOpen(true);
    setDrawerLoading(true);
    setConversation(null);
    try {
      const data = await fetchConversation(row.session_id, row.attendance_date);
      setConversation(data);
    } catch (err) {
      toast.error(
        getAxiosErrorMessage(err, { notAxiosMessage: "Não foi possível carregar a conversa." }),
      );
      setDrawerOpen(false);
    } finally {
      setDrawerLoading(false);
    }
  }

  function handleClearFilters() {
    const empty = emptyChatLogsSearchFilters();
    setFilters(empty);
    setDebouncedFilters(empty);
    setPage(1);
  }

  const filtersActive = hasActiveChatLogsFilters(debouncedFilters);
  const pageSize = 20;
  const totalPages = Math.max(1, Math.ceil(totalCount / pageSize));

  return (
    <>
      <AdminPageLayout
        pageTitle="Histórico de Chamados"
        metaDescription="Histórico de conversas WhatsApp"
        description="Monitoramento de atendimentos do bot WhatsApp, agrupados por morador e dia."
      >
        <ChatLogsFilterBar
          filters={filters}
          markets={markets}
          busy={loading}
          onChange={setFilters}
          onClear={handleClearFilters}
        />

        <ChatLogsTable
          rows={rows}
          loading={loading}
          filtersActive={filtersActive}
          onViewConversation={handleViewConversation}
        />

        {!loading && totalCount > 0 ? (
          <div className="mt-6 flex flex-col items-center justify-between gap-3 sm:flex-row">
            <p className="text-sm text-gray-500">
              Página {page} de {totalPages} · {totalCount} atendimento
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

      <ChatConversationDrawer
        open={drawerOpen}
        loading={drawerLoading}
        conversation={conversation}
        onClose={() => setDrawerOpen(false)}
      />
    </>
  );
}

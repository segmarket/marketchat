import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";
import AdminPageLayout from "../../components/layout/AdminPageShell";
import SupportTicketDetailHeader from "../../components/supportTickets/SupportTicketDetailHeader";
import SupportTicketDetailToolbar from "../../components/supportTickets/SupportTicketDetailToolbar";
import SupportTicketEmptyState from "../../components/supportTickets/SupportTicketEmptyState";
import SupportTicketListPanel from "../../components/supportTickets/SupportTicketListPanel";
import SupportTicketReplyBox from "../../components/supportTickets/SupportTicketReplyBox";
import SupportTicketThread from "../../components/supportTickets/SupportTicketThread";
import {
  fetchSupportTicket,
  fetchSupportTickets,
  patchSupportTicket,
  postSupportTicketReply,
} from "../../features/supportTickets/api";
import type { SupportTicketDetail, SupportTicketSummary } from "../../features/supportTickets/types";
import { getAxiosErrorMessage } from "../../utils/apiError";

function isTicketLocked(status: string): boolean {
  return status === "CLOSED" || status === "RESOLVED";
}

export default function SupportHistoryPage() {
  const [tickets, setTickets] = useState<SupportTicketSummary[]>([]);
  const [listLoading, setListLoading] = useState(true);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [detail, setDetail] = useState<SupportTicketDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [replyText, setReplyText] = useState("");
  const [replySending, setReplySending] = useState(false);
  const [resolving, setResolving] = useState(false);

  const hasSelection = selectedId !== null;
  const selectedSummary = tickets.find((t) => t.id === selectedId) ?? null;

  const loadTickets = useCallback(async () => {
    setListLoading(true);
    try {
      const data = await fetchSupportTickets();
      setTickets(data);
      setSelectedId((prev) => {
        if (prev !== null && data.some((t) => t.id === prev)) return prev;
        return prev;
      });
    } catch (err) {
      toast.error(
        getAxiosErrorMessage(err, { notAxiosMessage: "Não foi possível carregar os chamados." }),
      );
    } finally {
      setListLoading(false);
    }
  }, []);

  const loadDetail = useCallback(async (id: number) => {
    setDetailLoading(true);
    try {
      const data = await fetchSupportTicket(id);
      setDetail(data);
    } catch (err) {
      setDetail(null);
      toast.error(
        getAxiosErrorMessage(err, { notAxiosMessage: "Não foi possível carregar o chamado." }),
      );
    } finally {
      setDetailLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadTickets();
  }, [loadTickets]);

  useEffect(() => {
    if (selectedId === null) {
      setDetail(null);
      setDetailLoading(false);
      setReplyText("");
      return;
    }
    void loadDetail(selectedId);
  }, [selectedId, loadDetail]);

  function handleBackToList() {
    setSelectedId(null);
    setDetail(null);
    setDetailLoading(false);
    setReplyText("");
  }

  async function handleReply() {
    if (!selectedId || !replyText.trim() || replySending) return;
    setReplySending(true);
    try {
      await postSupportTicketReply(selectedId, replyText.trim());
      setReplyText("");
      toast.success("Resposta enviada.");
      await loadDetail(selectedId);
      await loadTickets();
    } catch (err) {
      toast.error(
        getAxiosErrorMessage(err, { notAxiosMessage: "Não foi possível enviar a resposta." }),
      );
    } finally {
      setReplySending(false);
    }
  }

  async function handleResolve() {
    if (!selectedId || resolving) return;
    setResolving(true);
    try {
      const updated = await patchSupportTicket(selectedId, { status: "RESOLVED" });
      setDetail(updated);
      toast.success("Chamado marcado como resolvido.");
      await loadTickets();
    } catch (err) {
      toast.error(
        getAxiosErrorMessage(err, { notAxiosMessage: "Não foi possível atualizar o chamado." }),
      );
    } finally {
      setResolving(false);
    }
  }

  return (
    <AdminPageLayout
      pageTitle="Meus Chamados"
      metaTitle="Meus Chamados | Marketchat"
      metaDescription="Acompanhe chamados de suporte da sua empresa e converse com a equipe."
      description="Todos os chamados abertos pela sua empresa, com histórico de mensagens."
      panelClassName="!p-0 overflow-hidden"
    >
      <div className="flex min-h-[min(640px,calc(100vh-14rem))] w-full flex-col md:flex-row">
        {/* Lista: oculta no mobile quando há seleção; sempre visível no desktop */}
        <div
          className={`w-full shrink-0 flex-col border-gray-200 dark:border-gray-800 md:w-[38%] md:max-w-md md:border-r ${
            hasSelection ? "hidden md:flex" : "flex"
          }`}
        >
          <div className="border-b border-gray-100 px-4 py-3 dark:border-gray-800">
            <h3 className="text-sm font-semibold text-gray-800 dark:text-white/90">Chamados</h3>
          </div>
          <div className="min-h-0 flex-1 overflow-y-auto">
            <SupportTicketListPanel
              tickets={tickets}
              selectedId={selectedId}
              loading={listLoading}
              onSelect={setSelectedId}
            />
          </div>
        </div>

        {/* Detalhe: sempre visível no desktop (md+); no mobile só com seleção */}
        <div
          className={`min-h-[280px] min-w-0 flex-1 flex-col ${
            hasSelection ? "flex" : "hidden md:flex"
          }`}
        >
          {!hasSelection ? (
            <SupportTicketEmptyState />
          ) : detail ? (
            <>
              <SupportTicketDetailHeader
                ticket={detail}
                resolving={resolving}
                onBack={handleBackToList}
                onClose={handleBackToList}
                onResolve={() => void handleResolve()}
              />
              <SupportTicketThread ticket={detail} />
              <SupportTicketReplyBox
                value={replyText}
                disabled={false}
                sending={replySending}
                closed={isTicketLocked(detail.status)}
                onChange={setReplyText}
                onSubmit={() => void handleReply()}
              />
            </>
          ) : (
            <>
              <SupportTicketDetailToolbar
                title={detailLoading ? undefined : selectedSummary?.subject}
                onBack={handleBackToList}
                onClose={handleBackToList}
              />
              <div className="flex flex-1 items-center justify-center p-8 text-sm text-gray-500">
                {detailLoading
                  ? "Carregando conversa…"
                  : "Não foi possível exibir este chamado. Tente novamente."}
              </div>
            </>
          )}
        </div>
      </div>
    </AdminPageLayout>
  );
}

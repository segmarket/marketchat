import { useCallback, useEffect, useState } from "react";
import { Search } from "lucide-react";
import { toast } from "sonner";
import AdminPageLayout from "../../components/layout/AdminPageShell";
import InboxChatPane from "../../components/chatInbox/InboxChatPane";
import InboxSessionList from "../../components/chatInbox/InboxSessionList";
import InboxTabs, { type InboxTab } from "../../components/chatInbox/InboxTabs";
import { fetchInboxSessions } from "../../features/chatLogs/api";
import type { InboxSessionRow } from "../../features/chatLogs/types";
import { getAxiosErrorMessage } from "../../utils/apiError";

function tabToBotActive(tab: InboxTab): boolean | null {
  if (tab === "waiting") return false;
  if (tab === "bot") return true;
  return null;
}

export default function ChatLogsPage() {
  const [tab, setTab] = useState<InboxTab>("waiting");
  const [q, setQ] = useState("");
  const [debouncedQ, setDebouncedQ] = useState("");
  const [rows, setRows] = useState<InboxSessionRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedSessionId, setSelectedSessionId] = useState<number | null>(null);
  const [unreadTick, setUnreadTick] = useState(0);

  useEffect(() => {
    const timer = window.setTimeout(() => setDebouncedQ(q.trim()), 300);
    return () => window.clearTimeout(timer);
  }, [q]);

  const loadSessions = useCallback(
    async (opts?: { silent?: boolean }) => {
      if (!opts?.silent) setLoading(true);
      try {
        const data = await fetchInboxSessions({
          botActive: tabToBotActive(tab),
          q: debouncedQ || undefined,
          page: 1,
        });
        setRows(data.results);
        setSelectedSessionId((prev) => {
          if (prev == null) return prev;
          if (data.results.some((r) => r.session_id === prev)) return prev;
          return null;
        });
      } catch (err) {
        if (!opts?.silent) {
          toast.error(
            getAxiosErrorMessage(err, {
              notAxiosMessage: "Não foi possível carregar as conversas.",
            }),
          );
        }
      } finally {
        if (!opts?.silent) setLoading(false);
      }
    },
    [tab, debouncedQ],
  );

  useEffect(() => {
    void loadSessions();
  }, [loadSessions]);

  // Poll da lista a cada 10s
  useEffect(() => {
    const id = window.setInterval(() => {
      if (document.visibilityState !== "visible") return;
      void loadSessions({ silent: true });
    }, 10000);
    return () => window.clearInterval(id);
  }, [loadSessions]);

  function handleSelect(row: InboxSessionRow) {
    setSelectedSessionId(row.session_id);
  }

  function handleTabChange(next: InboxTab) {
    setTab(next);
    setSelectedSessionId(null);
  }

  const handleBotStatusChange = useCallback(
    (sessionId: number, isBotActive: boolean) => {
      const filter = tabToBotActive(tab);
      setRows((prev) => {
        const updated = prev.map((r) =>
          r.session_id === sessionId ? { ...r, is_bot_active: isBotActive } : r,
        );
        if (filter === null) return updated;
        return updated.filter((r) => r.is_bot_active === filter);
      });
    },
    [tab],
  );

  const handleSeenUpdate = useCallback(() => {
    setUnreadTick((t) => t + 1);
  }, []);

  return (
    <AdminPageLayout
      pageTitle="Atendimento"
      metaDescription="Inbox de atendimento WhatsApp"
      className="flex h-full min-h-0 flex-1 flex-col overflow-hidden"
      panelClassName="!p-0 flex min-h-0 flex-1 flex-col overflow-hidden"
    >
      <div className="flex min-h-0 flex-1">
        <aside className="flex h-full min-h-0 w-full max-w-[360px] shrink-0 flex-col border-r border-gray-200 dark:border-gray-800">
          <InboxTabs value={tab} onChange={handleTabChange} />
          <div className="shrink-0 border-b border-gray-200 px-3 py-2 dark:border-gray-800">
            <label className="relative block">
              <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-gray-400" />
              <input
                type="search"
                value={q}
                onChange={(e) => setQ(e.target.value)}
                placeholder="Buscar nome ou telefone…"
                className="w-full rounded-xl border border-gray-200 bg-gray-50 py-2 pl-9 pr-3 text-sm text-gray-800 outline-none focus:border-brand-400 focus:ring-2 focus:ring-brand-100 dark:border-gray-700 dark:bg-gray-950 dark:text-white/90"
              />
            </label>
          </div>
          <InboxSessionList
            rows={rows}
            loading={loading}
            selectedSessionId={selectedSessionId}
            onSelect={handleSelect}
            unreadTick={unreadTick}
          />
        </aside>

        <InboxChatPane
          sessionId={selectedSessionId}
          onBotStatusChange={handleBotStatusChange}
          onSeenUpdate={handleSeenUpdate}
        />
      </div>
    </AdminPageLayout>
  );
}

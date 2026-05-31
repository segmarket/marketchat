import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { toast } from "sonner";
import {
  fetchLatestNotifications,
  markAllNotificationsRead,
  markNotificationRead,
} from "../features/notifications/api";
import type { NotificationItem } from "../features/notifications/types";
import { getAxiosErrorMessage } from "../utils/apiError";
import { useAuth } from "./AuthContext";

const POLL_INTERVAL_MS = 15_000;

type NotificationsContextValue = {
  items: NotificationItem[];
  unreadCount: number;
  loading: boolean;
  refresh: () => Promise<void>;
  markRead: (id: number) => Promise<void>;
  markAllRead: () => Promise<void>;
};

const NotificationsContext = createContext<NotificationsContextValue | null>(null);

function storageKey(tenantId: number): string {
  return `notifications_seen_${tenantId}`;
}

function loadSeenIds(tenantId: number): Set<number> {
  try {
    const raw = sessionStorage.getItem(storageKey(tenantId));
    if (!raw) return new Set();
    const parsed = JSON.parse(raw) as number[];
    return new Set(parsed.filter((id) => typeof id === "number"));
  } catch {
    return new Set();
  }
}

function saveSeenIds(tenantId: number, ids: Set<number>): void {
  sessionStorage.setItem(storageKey(tenantId), JSON.stringify([...ids]));
}

function showCriticalToast(item: NotificationItem): void {
  const marketName = item.market_name?.trim() || "do condomínio";
  toast.error("Incidente crítico detectado", {
    description: `Morador relatou um problema no mercado ${marketName}. Abra o menu de notificações para ver os detalhes.`,
    duration: 8000,
  });
}

type ProviderProps = {
  children: ReactNode;
  pollingEnabled?: boolean;
};

export function NotificationsProvider({
  children,
  pollingEnabled = true,
}: ProviderProps) {
  const { tenant, isAuthenticated } = useAuth();
  const tenantId = tenant?.id ?? null;

  const [items, setItems] = useState<NotificationItem[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [loading, setLoading] = useState(false);

  const seenIdsRef = useRef<Set<number>>(new Set());
  const initializedRef = useRef(false);

  useEffect(() => {
    initializedRef.current = false;
    seenIdsRef.current = tenantId ? loadSeenIds(tenantId) : new Set();
  }, [tenantId]);

  const processNewNotifications = useCallback(
    (results: NotificationItem[]) => {
      if (!tenantId) return;

      if (!initializedRef.current) {
        for (const item of results) {
          seenIdsRef.current.add(item.id);
        }
        saveSeenIds(tenantId, seenIdsRef.current);
        initializedRef.current = true;
        return;
      }

      for (const item of results) {
        if (seenIdsRef.current.has(item.id)) continue;
        seenIdsRef.current.add(item.id);
        if (item.severity === "CRITICAL") {
          showCriticalToast(item);
        }
      }
      saveSeenIds(tenantId, seenIdsRef.current);
    },
    [tenantId],
  );

  const refresh = useCallback(async () => {
    if (!tenantId || !isAuthenticated) return;
    setLoading(true);
    try {
      const data = await fetchLatestNotifications();
      const results = Array.isArray(data.results) ? data.results : [];
      setItems(results);
      setUnreadCount(typeof data.unread_count === "number" ? data.unread_count : 0);
      processNewNotifications(results);
    } catch (err) {
      console.error(getAxiosErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }, [tenantId, isAuthenticated, processNewNotifications]);

  useEffect(() => {
    if (!pollingEnabled || !tenantId || !isAuthenticated) {
      setItems([]);
      setUnreadCount(0);
      return;
    }

    void refresh();
    const timer = window.setInterval(() => {
      void refresh();
    }, POLL_INTERVAL_MS);

    return () => window.clearInterval(timer);
  }, [pollingEnabled, tenantId, isAuthenticated, refresh]);

  const markRead = useCallback(
    async (id: number) => {
      const previousItems = items;
      const previousCount = unreadCount;

      setItems((prev) => prev.filter((n) => n.id !== id));
      setUnreadCount((prev) => Math.max(0, prev - 1));

      try {
        await markNotificationRead(id);
        seenIdsRef.current.add(id);
        if (tenantId) saveSeenIds(tenantId, seenIdsRef.current);
      } catch (err) {
        setItems(previousItems);
        setUnreadCount(previousCount);
        toast.error(getAxiosErrorMessage(err));
      }
    },
    [items, unreadCount, tenantId],
  );

  const markAllRead = useCallback(async () => {
    const previousItems = items;
    const previousCount = unreadCount;

    setItems([]);
    setUnreadCount(0);

    try {
      await markAllNotificationsRead();
      for (const item of previousItems) {
        seenIdsRef.current.add(item.id);
      }
      if (tenantId) saveSeenIds(tenantId, seenIdsRef.current);
    } catch (err) {
      setItems(previousItems);
      setUnreadCount(previousCount);
      toast.error(getAxiosErrorMessage(err));
    }
  }, [items, unreadCount, tenantId]);

  const value = useMemo(
    () => ({
      items,
      unreadCount,
      loading,
      refresh,
      markRead,
      markAllRead,
    }),
    [items, unreadCount, loading, refresh, markRead, markAllRead],
  );

  return (
    <NotificationsContext.Provider value={value}>{children}</NotificationsContext.Provider>
  );
}

export function useNotifications(): NotificationsContextValue {
  const ctx = useContext(NotificationsContext);
  if (!ctx) {
    throw new Error("useNotifications deve ser usado dentro de NotificationsProvider");
  }
  return ctx;
}

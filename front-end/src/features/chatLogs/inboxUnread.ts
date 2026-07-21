const STORAGE_KEY = "marketchat.inbox.lastSeenBySession";

type LastSeenMap = Record<string, number>;

function readMap(): LastSeenMap {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return {};
    const parsed = JSON.parse(raw) as LastSeenMap;
    return parsed && typeof parsed === "object" ? parsed : {};
  } catch {
    return {};
  }
}

function writeMap(map: LastSeenMap): void {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(map));
  } catch {
    // ignore quota / private mode
  }
}

export function getLastSeenMessageId(sessionId: number): number {
  const map = readMap();
  const value = map[String(sessionId)];
  return typeof value === "number" && value > 0 ? value : 0;
}

export function markSessionSeen(sessionId: number, messageId: number): boolean {
  if (!messageId || messageId <= 0) return false;
  const map = readMap();
  const key = String(sessionId);
  const prev = map[key] ?? 0;
  if (messageId <= prev) return false;
  map[key] = messageId;
  writeMap(map);
  return true;
}

/** Badge estável: há inbound mais novo que o último visto nesta sessão. */
export function hasUnreadInbound(
  sessionId: number,
  lastInboundId: number | null | undefined,
): boolean {
  if (lastInboundId == null || lastInboundId <= 0) return false;
  return lastInboundId > getLastSeenMessageId(sessionId);
}

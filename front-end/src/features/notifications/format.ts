import type { NotificationSeverity } from "./types";

export function formatRelativeTime(isoDate: string): string {
  const date = new Date(isoDate);
  if (Number.isNaN(date.getTime())) return "";

  const diffMs = Date.now() - date.getTime();
  const diffSec = Math.floor(diffMs / 1000);
  if (diffSec < 60) return "agora";
  const diffMin = Math.floor(diffSec / 60);
  if (diffMin < 60) return `há ${diffMin} min`;
  const diffHr = Math.floor(diffMin / 60);
  if (diffHr < 24) return `há ${diffHr} h`;
  const diffDay = Math.floor(diffHr / 24);
  return `há ${diffDay} dia${diffDay === 1 ? "" : "s"}`;
}

export function severityStyles(severity: NotificationSeverity): {
  border: string;
  dot: string;
  title: string;
} {
  switch (severity) {
    case "CRITICAL":
      return {
        border: "border-error-200 dark:border-error-900/50",
        dot: "bg-error-500",
        title: "text-error-700 dark:text-error-400",
      };
    case "WARNING":
      return {
        border: "border-warning-200 dark:border-warning-900/50",
        dot: "bg-warning-500",
        title: "text-warning-700 dark:text-warning-400",
      };
    default:
      return {
        border: "border-gray-200 dark:border-gray-700",
        dot: "bg-gray-400",
        title: "text-gray-800 dark:text-white/90",
      };
  }
}

export function unreadBadgeLabel(count: number): string {
  if (count <= 0) return "";
  if (count > 9) return "9+";
  return String(count);
}

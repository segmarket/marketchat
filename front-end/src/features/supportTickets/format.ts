import type { SupportTicketStatus } from "./types";

const STATUS_LABELS: Record<SupportTicketStatus, string> = {
  NEW: "Novo",
  IN_PROGRESS: "Em andamento",
  RESOLVED: "Resolvido",
  CLOSED: "Fechado",
};

export function ticketStatusLabel(status: string): string {
  return STATUS_LABELS[status as SupportTicketStatus] ?? (status || "—");
}

export function ticketStatusBadgeClass(status: string): string {
  switch (status) {
    case "NEW":
      return "bg-blue-50 text-blue-700 ring-blue-600/20 dark:bg-blue-500/10 dark:text-blue-400 dark:ring-blue-500/30";
    case "IN_PROGRESS":
      return "bg-orange-50 text-orange-800 ring-orange-600/20 dark:bg-orange-500/10 dark:text-orange-400 dark:ring-orange-500/30";
    case "RESOLVED":
      return "bg-emerald-50 text-emerald-700 ring-emerald-600/20 dark:bg-emerald-500/10 dark:text-emerald-400 dark:ring-emerald-500/30";
    case "CLOSED":
      return "bg-gray-100 text-gray-600 ring-gray-500/20 dark:bg-gray-800 dark:text-gray-400 dark:ring-gray-600/30";
    default:
      return "bg-gray-100 text-gray-700 ring-gray-500/20";
  }
}

export function formatTicketDate(iso: string): string {
  try {
    return new Intl.DateTimeFormat("pt-BR", {
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    }).format(new Date(iso));
  } catch {
    return iso;
  }
}

export function truncateRoute(route: string, max = 36): string {
  if (route.length <= max) return route;
  return `${route.slice(0, max - 1)}…`;
}

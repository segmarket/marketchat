import Badge from "../ui/badge/Badge";
import type { InvoiceStatus } from "../../features/settings/types";

const CONFIG: Record<InvoiceStatus, { color: "success" | "warning" | "error"; label: string }> = {
  PAID: { color: "success", label: "Pago" },
  PENDING: { color: "warning", label: "Pendente" },
  OVERDUE: { color: "error", label: "Atrasado" },
};

export default function InvoiceStatusBadge({ status }: { status: InvoiceStatus }) {
  const cfg = CONFIG[status] ?? { color: "warning" as const, label: status };
  return (
    <Badge color={cfg.color} size="sm">
      {cfg.label}
    </Badge>
  );
}

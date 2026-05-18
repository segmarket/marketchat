import { DollarSign, PackageX, ShoppingBag, TrendingUp } from "lucide-react";
import {
  formatBRL,
  formatConversionTooltip,
  formatPercent,
} from "../../features/sales/format";
import type { SalesMetrics } from "../../features/sales/types";

type Props = {
  metrics: SalesMetrics | null;
  loading?: boolean;
};

function KpiCard({
  title,
  value,
  subtitle,
  icon,
  valueClassName = "text-gray-800 dark:text-white/90",
}: {
  title: string;
  value: string;
  subtitle?: string;
  icon: React.ReactNode;
  valueClassName?: string;
}) {
  return (
    <div className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm dark:border-gray-800 dark:bg-white/[0.03]">
      <div className="flex items-start justify-between gap-2">
        <div>
          <p className="text-xs font-medium uppercase tracking-wide text-gray-500">{title}</p>
          <p className={`mt-2 text-2xl font-semibold ${valueClassName}`}>{value}</p>
          {subtitle ? (
            <p className="mt-1 text-xs text-gray-500" title={subtitle}>
              {subtitle}
            </p>
          ) : null}
        </div>
        <div className="rounded-lg bg-gray-50 p-2 text-gray-500 dark:bg-white/5">{icon}</div>
      </div>
    </div>
  );
}

export default function SalesKpiBar({ metrics, loading = false }: Props) {
  if (loading || !metrics) {
    return (
      <div className="mb-6 grid grid-cols-1 gap-4 md:grid-cols-4">
        {[1, 2, 3, 4].map((i) => (
          <div
            key={i}
            className="h-28 animate-pulse rounded-xl border border-gray-200 bg-gray-50 dark:border-gray-800 dark:bg-white/5"
          />
        ))}
      </div>
    );
  }

  const conversionHint = formatConversionTooltip(metrics.conversion_rate);

  return (
    <div className="mb-6 grid grid-cols-1 gap-4 md:grid-cols-4">
      <KpiCard
        title="Faturamento total"
        value={formatBRL(metrics.total_revenue)}
        icon={<DollarSign className="size-6 text-green-600" />}
        valueClassName="text-green-600"
      />
      <KpiCard
        title="Vendas concluídas"
        value={String(metrics.total_orders)}
        icon={<ShoppingBag className="size-6" />}
      />
      <KpiCard
        title="Ticket médio"
        value={formatBRL(metrics.average_ticket)}
        icon={<TrendingUp className="size-6" />}
      />
      <KpiCard
        title="Carrinhos abandonados"
        value={String(metrics.abandoned_orders)}
        subtitle={`Conversão: ${formatPercent(metrics.conversion_rate)} · ${conversionHint}`}
        icon={<PackageX className="size-6 text-amber-600" />}
        valueClassName="text-amber-700"
      />
    </div>
  );
}

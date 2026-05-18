import {
  ArrowDownIcon,
  ArrowUpIcon,
  BoxIconLine,
  GroupIcon,
} from "../../icons";
import Badge from "../ui/badge/Badge";
import type { ChatbotAnalyticsCards } from "../../features/chatbotAnalytics/types";
import { formatCount, formatPercentChange } from "../../features/chatbotAnalytics/format";

type Props = {
  cards: ChatbotAnalyticsCards | null;
  loading?: boolean;
};

function ChangeBadge({ value }: { value: number }) {
  const isPositive = value >= 0;
  return (
    <Badge color={isPositive ? "success" : "error"}>
      {isPositive ? <ArrowUpIcon /> : <ArrowDownIcon />}
      {formatPercentChange(Math.abs(value))}
    </Badge>
  );
}

export default function EcommerceMetrics({ cards, loading = false }: Props) {
  const interactions = cards?.total_interactions ?? 0;
  const incidents = cards?.critical_incidents ?? 0;
  const interactionsChange = cards?.total_interactions_change_pct ?? 0;
  const incidentsChange = cards?.critical_incidents_change_pct ?? 0;

  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 md:gap-6">
      <div className="rounded-2xl border border-gray-200 bg-white p-5 dark:border-gray-800 dark:bg-white/[0.03] md:p-6">
        <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-gray-100 dark:bg-gray-800">
          <GroupIcon className="size-6 text-gray-800 dark:text-white/90" />
        </div>

        <div className="mt-5 flex items-end justify-between">
          <div>
            <span className="text-sm text-gray-500 dark:text-gray-400">
              Interações no mês
            </span>
            <h4 className="mt-2 text-title-sm font-bold text-gray-800 dark:text-white/90">
              {loading ? "—" : formatCount(interactions)}
            </h4>
          </div>
          {!loading && cards ? (
            <ChangeBadge value={interactionsChange} />
          ) : null}
        </div>
      </div>

      <div className="rounded-2xl border border-gray-200 bg-white p-5 dark:border-gray-800 dark:bg-white/[0.03] md:p-6">
        <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-gray-100 dark:bg-gray-800">
          <BoxIconLine className="size-6 text-gray-800 dark:text-white/90" />
        </div>
        <div className="mt-5 flex items-end justify-between">
          <div>
            <span className="text-sm text-gray-500 dark:text-gray-400">
              Incidentes críticos
            </span>
            <h4 className="mt-2 text-title-sm font-bold text-gray-800 dark:text-white/90">
              {loading ? "—" : formatCount(incidents)}
            </h4>
          </div>
          {!loading && cards ? (
            <ChangeBadge value={-incidentsChange} />
          ) : null}
        </div>
      </div>
    </div>
  );
}

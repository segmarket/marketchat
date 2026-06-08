import {
  ArrowDownIcon,
  ArrowUpIcon,
  BoxIconLine,
  GroupIcon,
} from "../../icons";
import Badge from "../ui/badge/Badge";
import MetricHelpTooltip from "../ui/help-tooltip/MetricHelpTooltip";
import type { ChatbotAnalyticsCards } from "../../features/chatbotAnalytics/types";
import { formatCount, formatPercentChange } from "../../features/chatbotAnalytics/format";
import { METRIC_HELP_TEXTS } from "../../features/chatbotAnalytics/metricHelpTexts";

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
    <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-4">
      <div className="rounded-2xl border border-gray-200 bg-white p-5 dark:border-gray-800 dark:bg-white/[0.03] md:p-6 lg:col-span-2">
        <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-gray-100 dark:bg-gray-800">
          <GroupIcon className="size-6 text-gray-800 dark:text-white/90" />
        </div>

        <div className="mt-5 flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <MetricHelpTooltip
              label="Interações no mês"
              helpText={METRIC_HELP_TEXTS.interactions}
            />
            <h4 className="mt-2 text-title-sm font-bold text-gray-800 dark:text-white/90">
              {loading ? "—" : formatCount(interactions)}
            </h4>
          </div>
          {!loading && cards ? (
            <ChangeBadge value={interactionsChange} />
          ) : null}
        </div>
      </div>

      <div className="rounded-2xl border border-gray-200 bg-white p-5 dark:border-gray-800 dark:bg-white/[0.03] md:p-6 lg:col-span-2">
        <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-gray-100 dark:bg-gray-800">
          <BoxIconLine className="size-6 text-gray-800 dark:text-white/90" />
        </div>
        <div className="mt-5 flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <MetricHelpTooltip
              label="Incidentes críticos"
              helpText={METRIC_HELP_TEXTS.criticalIncidents}
            />
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
